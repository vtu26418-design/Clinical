"""Project isolation and declarative-only scientific storyboards."""
import copy
import json

import pytest
from fastapi.testclient import TestClient
from backend.app.main import create_app
from test_v5_platform import config_at, setup, PASSWORD


def document():
    return {'version':1,'title':'Study processing','source_notes':'NCT12345678: source notes only.',
            'scene':'pipeline','steps':[{'id':'one','title':'Source','caption':'Literal source data.',
                'narration':'Read the source.','focus':'input','labels':['Source']}],
            'settings':{'accent':'#32b8af','background':'midnight','detail':'standard','speed':1,
                'show_labels':True,'camera':'orbit','voice_uri':'','voice_rate':1}}


@pytest.fixture
def science_owner(tmp_path):
    with TestClient(create_app(config_at(tmp_path))) as client:
        setup(client)
        project=client.post('/api/v5/projects',json={'name':'Scientific workspace'}).json()
        client.headers['X-Project-ID']=project['id']
        yield client,project


def test_storyboard_crud_is_scoped_and_conflict_checked(science_owner):
    client,project=science_owner
    path='/api/v5/science/storyboards'
    response=client.post(path,json={'document':document()})
    assert response.status_code==201,response.text
    saved=response.json(); identifier=saved['id']
    assert client.get(path).json()['items'][0]['id']==identifier
    changed=document(); changed['steps'][0]['caption']='<script>literal text only</script>'
    response=client.put(path+'/'+identifier,json={'document':changed,'expected_updated_at':saved['updated_at']})
    assert response.status_code==200,response.text
    assert response.json()['document']['steps'][0]['caption']==changed['steps'][0]['caption']
    assert client.put(path+'/'+identifier,json={'document':document(),'expected_updated_at':saved['updated_at']}).status_code==409
    other=client.post('/api/v5/projects',json={'name':'Other project'}).json()
    client.headers['X-Project-ID']=other['id']
    assert client.get(path+'/'+identifier).status_code==404
    assert client.delete(path+'/'+identifier).status_code==404
    client.headers['X-Project-ID']=project['id']
    assert client.delete(path+'/'+identifier).status_code==204
    assert client.get(path+'/'+identifier).status_code==404


@pytest.mark.parametrize('mutate',[
    lambda d:d.update(version=True),lambda d:d.update(scene='javascript'),
    lambda d:d.update(__proto__={}),lambda d:d['settings'].update(script='bad'),
    lambda d:d['steps'].append(copy.deepcopy(d['steps'][0])),
    lambda d:d['settings'].update(show_labels='yes'),
    lambda d:d['settings'].update(voice_rate=float('inf')),
])
def test_storyboard_rejects_unsupported_or_ambiguous_data(science_owner,mutate):
    client,_=science_owner; value=document();mutate(value)
    # Python's permissive Infinity encoding is deliberately sent as raw JSON.
    response=client.post('/api/v5/science/storyboards',content=json.dumps({'document':value}),headers={'Content-Type':'application/json'})
    assert response.status_code==422,response.text


def test_reviewers_read_but_cannot_write_or_draft(science_owner):
    client,project=science_owner
    path='/api/v5/science/storyboards'
    saved=client.post(path,json={'document':document()}).json()
    invite=client.post('/api/v5/projects/'+project['id']+'/members',json={'email':'science-reviewer@example.org','name':'Reviewer','role':'reviewer'}).json()['invitation_token']
    with TestClient(client.app) as reviewer:
        assert reviewer.post('/api/v5/auth/accept-invite',json={'token':invite,'password':PASSWORD,'name':'Reviewer'}).status_code==200
        reviewer.headers['X-Project-ID']=project['id']
        assert reviewer.get(path+'/'+saved['id']).status_code==200
        assert reviewer.post(path,json={'document':document()}).status_code==403
        assert reviewer.delete(path+'/'+saved['id']).status_code==403
        assert reviewer.post('/api/v5/science/draft',json={'topic':'Study','source_notes':'NCT source','scene':'pipeline','provider':'auto'}).status_code==403


def test_optional_provider_failure_does_not_block_manual_editor(science_owner):
    client,_=science_owner
    response=client.post('/api/v5/science/draft',json={'topic':'Study','source_notes':'NCT12345678 source notes','scene':'pipeline','provider':'gemini'})
    assert response.status_code==503,response.text
    assert client.post('/api/v5/science/storyboards',json={'document':document()}).status_code==201


def test_provider_draft_is_strict_and_preserves_source(science_owner,monkeypatch):
    from backend.app.services import assistant_service
    client,_=science_owner
    def provider(*args,**kwargs):
        value=document();value['source_notes']='provider changed the source'
        return {'reply':json.dumps(value),'provider':'Test provider','provider_id':'gemini','model':'controlled'}
    monkeypatch.setattr(assistant_service,'assist',provider)
    monkeypatch.setattr(assistant_service,'provider_candidates',lambda *args:['gemini'])
    body={'topic':'Study','source_notes':'NCT12345678 unchanged evidence','scene':'pipeline','provider':'gemini'}
    response=client.post('/api/v5/science/draft',json=body)
    assert response.status_code==200,response.text
    assert response.json()['document']['source_notes']==body['source_notes']
    assert response.json()['origin']['needs_review'] is True
    assert response.json()['origin']['provider']=='gemini'
    draft=response.json();draft['document']['settings']['accent']='#118899'
    saved=client.post('/api/v5/science/storyboards',json=draft)
    assert saved.status_code==201,saved.text
    record=saved.json()
    assert record['origin']['edited'] is True
    assert record['origin']['verification']=='server_receipt'
    assert client.get('/api/v5/science/storyboards/'+record['id']).json()['origin']['provider']=='gemini'
    updated=client.put('/api/v5/science/storyboards/'+record['id'],json={'document':document()})
    assert updated.json()['origin']['generated'] is True


def test_contacted_provider_failures_count_against_project_budget(science_owner,monkeypatch):
    from backend.app.services import assistant_service
    client,project=science_owner;calls=[]
    monkeypatch.setattr(assistant_service,'provider_candidates',lambda *args:['gemini'])
    def invalid(*args,**kwargs):
        calls.append(True)
        return {'reply':'not JSON','provider_id':'gemini','model':'controlled'}
    monkeypatch.setattr(assistant_service,'assist',invalid)
    assert client.put('/api/v5/projects/'+project['id']+'/settings',json={'chat_daily_limit':1}).status_code==200
    body={'topic':'Study','source_notes':'NCT12345678 source','scene':'pipeline','provider':'gemini'}
    assert client.post('/api/v5/science/draft',json=body).status_code==502
    assert client.post('/api/v5/science/draft',json=body).status_code==429
    assert len(calls)==1
    assert client.get('/api/v5/projects/'+project['id']+'/usage').json()['chat_requests_today']==1


def test_imported_origin_cannot_claim_other_project_server_receipt(science_owner,monkeypatch):
    from backend.app.services import assistant_service
    client,project=science_owner
    monkeypatch.setattr(assistant_service,'provider_candidates',lambda *args:['gemini'])
    monkeypatch.setattr(assistant_service,'assist',lambda *args,**kw:{'reply':json.dumps(document()),'provider_id':'gemini','model':'controlled'})
    draft=client.post('/api/v5/science/draft',json={'topic':'Study','source_notes':'Actual notes','scene':'pipeline','provider':'gemini'}).json()
    other=client.post('/api/v5/projects',json={'name':'Imported explanation'}).json()
    client.headers['X-Project-ID']=other['id']
    saved=client.post('/api/v5/science/storyboards',json=draft)
    assert saved.status_code==201,saved.text
    assert saved.json()['origin']['generated'] is True
    assert saved.json()['origin']['verification']=='declared_import'


def test_owner_ai_toggle_blocks_provider_calls_but_preserves_manual_editor(science_owner,monkeypatch):
    from backend.app.services import assistant_service
    client,project=science_owner
    def forbidden(*args,**kwargs):raise AssertionError('A disabled project cannot contact a provider.')
    monkeypatch.setattr(assistant_service,'assist',forbidden)
    response=client.put('/api/v5/projects/'+project['id']+'/settings',json={'allow_ai':False})
    assert response.status_code==200,response.text
    assert response.json()['allow_ai'] is False
    assert client.post('/api/v5/science/draft',json={'topic':'Study','source_notes':'Source notes','scene':'pipeline','provider':'auto'}).status_code==403
    conversation=client.post('/api/v5/conversations',json={'title':'Disabled provider'}).json()
    assert client.post('/api/v5/conversations/'+conversation['id']+'/messages',json={'message':'Explain','dataset_id':'sample-fixture'}).status_code==403
    assert client.post('/api/v5/science/storyboards',json={'document':document()}).status_code==201
