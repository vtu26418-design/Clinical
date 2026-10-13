"""Behavioral coverage for the v5 security boundary and durable platform."""
from pathlib import Path
import time

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app

PASSWORD = 'a test password that is long enough'
TOKEN = 'setup-token-only-for-this-test-123456'


def config_at(tmp_path, **kwargs):
    return Settings(storage_dir=str(tmp_path), database_url='', auth_mode='session',
                    setup_token=TOKEN, openai_api_key='', gemini_api_key='',
                    anthropic_api_key='', compatible_api_key='', _env_file=None, **kwargs)


def setup(client):
    response = client.post('/api/v5/auth/setup', json={'email':'owner@example.org', 'password':PASSWORD, 'name':'Owner', 'setup_token':TOKEN})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def owner(tmp_path):
    app = create_app(config_at(tmp_path))
    with TestClient(app) as client:
        setup(client)
        project = client.post('/api/v5/projects', json={'name':'First project'}).json()
        client.headers['X-Project-ID'] = project['id']
        yield client, project


def test_bootstrap_requires_auth_and_setup_is_single_use(tmp_path):
    with TestClient(create_app(config_at(tmp_path))) as client:
        response = client.get('/api/v5/bootstrap')
        assert response.status_code == 200
        assert response.json()['auth_required'] and response.json()['setup_required']
        assert client.get('/api/v1/datasets').status_code == 401
        assert client.post('/api/v5/auth/setup', json={'email':'owner@example.org','password':PASSWORD,'name':'Owner','setup_token':'wrong'}).status_code == 403
        result = setup(client)
        assert 'password' not in str(result)
        assert client.post('/api/v5/auth/setup', json={'email':'x@example.org','password':PASSWORD,'name':'X','setup_token':TOKEN}).status_code == 409
        assert 'HttpOnly' in client.post('/api/v5/auth/login', json={'email':'owner@example.org','password':PASSWORD}).headers['set-cookie']
        assert client.post('/api/v5/auth/logout').status_code == 200
        assert client.get('/api/v5/projects').status_code == 401
        assert client.get('/api/v1/datasets', headers={'Authorization':'Bearer anything'}).status_code == 401


def test_production_rejects_anonymous_mode_and_sqlite(tmp_path):
    with pytest.raises(ValueError, match='local'):
        create_app(config_at(tmp_path, app_env='production', auth_mode_override='local').model_copy(update={'auth_mode':'local'}))
    with pytest.raises(ValueError, match='PostgreSQL'):
        create_app(config_at(tmp_path, app_env='production'))


def test_cross_project_research_and_saved_chat_isolation(owner):
    client, first = owner
    data = client.post('/api/v1/datasets/upload', files={'file':('trial.csv', b'nct_id,title\nNCT1,Private trial\n','text/csv')}).json()
    chat = client.post('/api/v5/conversations', json={'title':'Private discussion'}).json()
    second = client.post('/api/v5/projects', json={'name':'Second project'}).json()
    client.headers['X-Project-ID'] = second['id']
    assert all(d['id'] != data['id'] for d in client.get('/api/v1/datasets').json()['items'])
    for path in ['/api/v1/overview','/api/v1/exports/studies.json','/api/v1/research/workspace']:
        assert client.get(path, params={'dataset_id':data['id'],'nct_id':'NCT1'}).status_code == 404
    assert client.get('/api/v5/conversations/'+chat['id']).status_code == 404
    assert client.get('/api/v5/projects/'+first['id']+'/settings').status_code == 409
    assert client.get('/api/v1/datasets', headers={'X-Project-ID':'not-a-project'}).status_code == 403


def test_owner_invites_member_and_reviewer_cannot_mutate_research(owner):
    client, project = owner
    response = client.post('/api/v5/projects/'+project['id']+'/members', json={'email':'reviewer@example.org','name':'Reviewer','role':'reviewer'})
    assert response.status_code == 201, response.text
    invitation = response.json()['invitation_token']
    with TestClient(client.app) as reviewer:
        response = reviewer.post('/api/v5/auth/accept-invite', json={'token':invitation,'password':PASSWORD,'name':'Reviewer'})
        assert response.status_code == 200, response.text
        reviewer.headers['X-Project-ID'] = project['id']
        assert reviewer.get('/api/v1/datasets').status_code == 200
        for path in ['/api/v1/datasets/starter','/api/v1/experiments','/api/v1/research/scenarios','/api/v5/import/paste']:
            assert reviewer.post(path, json={}).status_code == 403
        assert reviewer.put('/api/v5/projects/'+project['id']+'/settings', json={'chat_daily_limit':5}).status_code == 403
        assert reviewer.post('/api/v5/projects/'+project['id']+'/members', json={'email':'third@example.org','role':'owner'}).status_code == 403
        assert reviewer.post('/api/v5/conversations',json={'title':'Mine'}).status_code == 201


def test_settings_validation_and_chat_persistence(owner, monkeypatch):
    from backend.app.services import assistant_service
    client, project = owner
    assert client.put('/api/v5/projects/'+project['id']+'/settings',json={'chat_daily_limit':-1}).status_code == 422
    assert client.put('/api/v5/projects/'+project['id']+'/settings',json={'chat_daily_limit':1,'default_provider':'auto'}).status_code == 200
    chat = client.post('/api/v5/conversations',json={'title':'Research notes'}).json()
    path = '/api/v5/conversations/'+chat['id']+'/messages'
    failure = client.post(path,json={'message':'Describe this study','dataset_id':'sample-fixture','nct_id':'NCT-SAMPLE-001'})
    assert failure.status_code == 503
    saved = client.get('/api/v5/conversations/'+chat['id']).json()
    assert saved['messages'][-1]['status'] == 'failed'
    assert not any(m['role'] == 'assistant' for m in saved['messages'])
    # Requests that fail before a provider call do not consume the daily budget.
    seen = []
    def controlled(config, message, context, provider=None):
        seen.append(context)
        return {'reply':'The sample is a software fixture.','provider':'Controlled test','provider_id':'test','model':'controlled','fallback_used':False,'attempted_providers':['test']}
    monkeypatch.setattr(assistant_service, 'assist', controlled)
    response = client.post(path,json={'message':'Explain PCI','dataset_id':'sample-fixture','nct_id':'NCT-SAMPLE-001'})
    assert response.status_code == 200, response.text
    assert response.json()['reply'] == 'The sample is a software fixture.'
    assert response.json()['references'][0]['dataset_id'] == 'sample-fixture'
    assert seen[0]['history'] and seen[0]['selected_study']['nct_id'] == 'NCT-SAMPLE-001'
    assert client.post(path,json={'message':'Another','dataset_id':'sample-fixture'}).status_code == 429
    assert client.get('/api/v5/projects/'+project['id']+'/usage').json()['chat_requests_today'] == 1
    with TestClient(create_app(client.app.state.settings)) as restarted:
        assert restarted.post('/api/v5/auth/login',json={'email':'owner@example.org','password':PASSWORD}).status_code == 200
        restarted.headers['X-Project-ID'] = project['id']
        again = restarted.get('/api/v5/conversations/'+chat['id']).json()
        assert again['messages'][-1]['content'] == response.json()['reply']


def test_session_expiration_and_csrf_origin(owner):
    client, project = owner
    assert client.post('/api/v5/conversations',json={'title':'Bad origin'},headers={'Origin':'https://evil.example'}).status_code == 403
    store = client.app.state.platform_store
    store.execute('UPDATE v5_sessions SET expires_at=0')
    assert client.get('/api/v1/datasets').status_code == 401


def test_import_rejects_unsafe_urls_and_paste_validates(owner):
    client, project = owner
    for url in ['http://clinicaltrials.gov/test.csv','https://127.0.0.1/x','https://169.254.169.254/latest','https://clinicaltrials.gov@evil.example/x','https://clinicaltrials.gov/x?token=secret']:
        assert client.post('/api/v5/import/url',json={'url':url}).status_code == 422
    pasted = client.post('/api/v5/import/paste',json={'content':'nct_id,title\nNCT9,Pasted trial\n','format':'csv','name':'Pasted source'})
    assert pasted.status_code == 201, pasted.text
    assert pasted.json()['row_count'] == 1
    assert client.post('/api/v5/import/paste',json={'content':'[]','format':'json'}).status_code == 422


def test_owner_only_training_and_viewer_chat_denied(owner):
    client, project = owner
    for role in ['researcher','viewer']:
        invitation=client.post('/api/v5/projects/'+project['id']+'/members',json={'email':role+'@example.org','name':role,'role':role}).json()['invitation_token']
        with TestClient(client.app) as member:
            member.post('/api/v5/auth/accept-invite',json={'token':invitation,'password':PASSWORD,'name':role})
            member.headers['X-Project-ID']=project['id']
            assert member.post('/api/v1/experiments',json={'dataset_id':'sample-fixture'}).status_code==403
            assert member.post('/api/v1/phase-experiments',json={'dataset_id':'sample-fixture'}).status_code==403
            if role=='viewer':
                assert member.post('/api/v5/conversations',json={}).status_code==403
            else:
                chat=member.post('/api/v5/conversations',json={'title':'Private researcher chat'}).json()
                assert client.get('/api/v5/conversations/'+chat['id']).status_code==404
                assert member.post('/api/v1/datasets/upload',files={'file':('x.csv',b'nct_id,title\nNCTNEW,Researcher\n','text/csv')}).status_code==201


def test_research_cors_keeps_cookie_credentials(owner):
    client, _=owner
    response=client.get('/api/v1/datasets',headers={'Origin':'http://localhost:5173'})
    assert response.headers.get('access-control-allow-credentials')=='true'


def test_url_resolution_redirect_and_size_limits(owner,monkeypatch):
    from backend.app.services import safe_import
    client,_=owner
    monkeypatch.setattr(safe_import.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('127.0.0.1',443))])
    assert client.post('/api/v5/import/url',json={'url':'https://clinicaltrials.gov/source.csv'}).status_code==422
    monkeypatch.setattr(safe_import.socket,'getaddrinfo',lambda *a,**k:[(2,1,6,'',('93.184.216.34',443))])
    state={'status':302,'length':'10'}
    class FakeResponse:
        @property
        def status(self):return state['status']
        def getheader(self,key,default=None):return {'Content-Length':state['length'],'Content-Type':'text/csv'}.get(key,default)
        def read(self,size):return b''
    class FakeConnection:
        def __init__(self,host,address,timeout):assert address=='93.184.216.34'
        def request(self,*a,**k):pass
        def getresponse(self):return FakeResponse()
        def close(self):pass
    monkeypatch.setattr(safe_import,'PinnedHTTPSConnection',FakeConnection)
    assert client.post('/api/v5/import/url',json={'url':'https://clinicaltrials.gov/source.csv'}).status_code==422
    state.update(status=200,length=str(10**9))
    assert client.post('/api/v5/import/url',json={'url':'https://clinicaltrials.gov/source.csv'}).status_code==413


def test_session_secret_not_persisted_and_password_not_plaintext(owner):
    client,_=owner
    store=client.app.state.platform_store
    user=store.one('SELECT * FROM v5_users LIMIT 1')
    assert user['password_hash'].startswith('scrypt$') and PASSWORD not in str(user)
    session=store.one('SELECT * FROM v5_sessions LIMIT 1')
    assert len(session['token_hash'])==64 and session['token_hash']!=client.cookies.get('cti_session')


def test_chunked_body_bound_before_json_parse(tmp_path):
    with TestClient(create_app(config_at(tmp_path,max_upload_bytes=1024))) as client:
        setup(client)
        project=client.post('/api/v5/projects',json={'name':'Bounded'}).json()
        client.headers['X-Project-ID']=project['id']
        # Unknown length and invalid JSON: the transport bound must win over parsing.
        response=client.post('/api/v5/import/paste',content=iter([b'{' + b'x'*40000,b'x'*40000]),headers={'Content-Type':'application/json'})
        assert response.status_code==413


def test_uploaded_json_uses_same_validation_and_raw_preservation(owner):
    client,project=owner
    raw=b'[{"nct_id":"NCTJSON1","title":"JSON trial","enrollment":24}]'
    response=client.post('/api/v1/datasets/upload',files={'file':('cohort.json',raw,'application/json')})
    assert response.status_code==201, response.text
    dataset=response.json()
    assert dataset['row_count']==1
    assert client.app.state.project_registry(project['id']).raw_path(dataset['id']).read_bytes()==raw
    for raw in [b'[]',b'{"nct_id":"NCT1"}',b'[{"nct_id":"NCT1","title":"Bad","enrollment":-1}]',b'[{"nct_id":"NCT1","title":["Nested"]}]']:
        assert client.post('/api/v1/datasets/upload',files={'file':('cohort.json',raw,'application/json')}).status_code==422


def test_uploaded_xlsx_first_sheet_and_blank_headers_rejected(owner):
    from io import BytesIO
    from zipfile import ZipFile
    client,_=owner
    def workbook(header='title'):
        out=BytesIO()
        with ZipFile(out,'w') as zip:
            zip.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>')
            zip.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
            zip.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Trials" sheetId="1" r:id="rId1"/></sheets></workbook>')
            zip.writestr('xl/_rels/workbook.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>')
            zip.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>nct_id</t></is></c><c r="B1" t="inlineStr"><is><t>{header}</t></is></c></row><row r="2"><c r="A2" t="inlineStr"><is><t>NCTXLSX</t></is></c><c r="B2" t="inlineStr"><is><t>Excel trial</t></is></c></row></sheetData></worksheet>')
        return out.getvalue()
    response=client.post('/api/v1/datasets/upload',files={'file':('cohort.xlsx',workbook(),'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')})
    assert response.status_code==201,response.text
    assert response.json()['row_count']==1
    assert client.post('/api/v1/datasets/upload',files={'file':('cohort.xlsx',workbook(''),'application/octet-stream')}).status_code==422


def test_json_nonstandard_numbers_and_duplicate_keys_rejected(owner):
    client,_=owner
    for raw in ['[{"nct_id":"A","title":"B","enrollment":NaN}]','[{"nct_id":"A","nct_id":"B","title":"C"}]']:
        assert client.post('/api/v5/import/paste',json={'format':'json','content':raw}).status_code==422
        assert client.post('/api/v1/datasets/upload',files={'file':('cohort.json',raw.encode(),'application/json')}).status_code==422


def test_protocol_review_evidence_and_project_isolation(owner):
    client, first = owner
    result = client.post('/api/v5/protocols/text', json={'title':'Version one', 'text':'Phase II randomized study.\nTarget enrollment: 120\nPatients attend site visits.'})
    assert result.status_code == 201, result.text
    doc = result.json()
    assert doc['features']['enrollment'] == 120 and doc['evidence'][0]['page'] == 1
    reviewed = client.post('/api/v5/protocols/'+doc['id']+'/review', json={'status':'corrected','notes':'Checked the final protocol document','fields':{'enrollment':140}})
    assert reviewed.status_code == 200
    assert reviewed.json()['features']['enrollment'] == 120
    assert reviewed.json()['reviewed_features']['enrollment'] == 140
    assert reviewed.json()['source_sha256'] == doc['source_sha256']
    other = client.post('/api/v5/projects', json={'name':'Isolated evidence'}).json()
    client.headers['X-Project-ID'] = other['id']
    assert client.get('/api/v5/protocols/'+doc['id']).status_code == 404
    assert client.get('/api/v5/protocols').json()['items'] == []
    assert client.post('/api/v5/protocols/text', json={'title':'Wrong family', 'text':'A sufficiently long source text for extraction.', 'group_id':doc['group_id']}).status_code == 404
    client.headers['X-Project-ID'] = first['id']
    assert client.post('/api/v5/protocols/upload', data={'title':'Invalid PDF'}, files={'file':('bad.pdf',b'not a pdf','application/pdf')}).status_code == 422
