"""v5.2 source, project and verification boundaries; upstream traffic is mocked."""
import time
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app

PASSWORD = 'a sufficiently long test password'
SETUP = 'test-only-setup-token-1234567890'
EVIDENCE = {'source':'pubmed','id':'1234','title':'Trial paper','summary':'A cited result',
            'url':'https://pubmed.ncbi.nlm.nih.gov/1234/','citation':'PubMed PMID 1234',
            'published_at':'2025','retrieved_at':'2026-10-11T12:00:00+00:00'}


def configuration(tmp_path, **kw):
    return Settings(storage_dir=str(tmp_path), database_url='', auth_mode='session', setup_token=SETUP,
                    mail_api_key='', mail_from='', public_base_url='', _env_file=None, **kw)


def owner(client):
    assert client.post('/api/v5/auth/setup', json={'email':'owner@example.org','name':'Owner',
                        'password':PASSWORD,'setup_token':SETUP}).status_code == 201


@pytest.fixture
def workspace(tmp_path,monkeypatch):
    from backend.app import v52
    monkeypatch.setattr(v52,'search',lambda source,query,limit:{'source':source,'query':query,'items':[EVIDENCE],
        'total':1,'limit':limit,'retrieved_at':EVIDENCE['retrieved_at']})
    with TestClient(create_app(configuration(tmp_path))) as client:
        owner(client)
        project = client.post('/api/v5/projects', json={'name':'Evidence'}).json()
        client.headers['X-Project-ID'] = project['id']
        assert client.get('/api/v5.2/research/search',params={'source':'pubmed','q':'trial'}).status_code == 200
        yield client, project


@pytest.mark.parametrize('source', ['clinicaltrials','pubmed','openfda'])
def test_sources_fixed_hosts_and_citations(source):
    from backend.app.research_sources import search
    seen = []
    def upstream(request):
        seen.append(request)
        if request.url.host == 'clinicaltrials.gov':
            return httpx.Response(200,json={'totalCount':1,'studies':[{'protocolSection':{
                'identificationModule':{'nctId':'NCT01234567','briefTitle':'<b>Real study</b>'},
                'descriptionModule':{'briefSummary':'A &amp; B'},
                'statusModule':{'lastUpdatePostDateStruct':{'date':'2025-01-01'}}}}]})
        if request.url.path.endswith('esearch.fcgi'):
            return httpx.Response(200,json={'esearchresult':{'idlist':['1234'],'count':'1'}})
        if request.url.path.endswith('esummary.fcgi'):
            return httpx.Response(200,json={'result':{'uids':['1234'],'1234':{'title':'<i>Trial paper</i>', 'pubdate':'2025'}}})
        return httpx.Response(200,json={'meta':{'results':{'total':1}},'results':[{
            'id':'label-123','effective_time':'20250101','openfda':{'brand_name':['Example']},
            'indications_and_usage':['Label information']} ]})
    with httpx.Client(transport=httpx.MockTransport(upstream)) as client:
        result = search(source,'cancer',3,client=client)
    assert result['total'] == 1 and len(result['items']) == 1
    item = result['items'][0]
    assert item['source'] == source and item['citation'] and item['retrieved_at']
    assert item['url'].startswith('https://') and '<' not in item['title']
    assert {r.url.host for r in seen} <= {'clinicaltrials.gov','eutils.ncbi.nlm.nih.gov','api.fda.gov'}
    assert len(seen) <= 2


@pytest.mark.parametrize('kind',['timeout','malformed','oversize','redirect'])
def test_sources_bound_untrusted_upstream(kind):
    from backend.app.research_sources import search, SourceUnavailable
    def upstream(request):
        if kind == 'timeout':
            raise httpx.ReadTimeout('sensitive provider details',request=request)
        if kind == 'malformed':
            return httpx.Response(200,json={'studies':'not a list'})
        if kind == 'oversize':
            return httpx.Response(200,content=b'x' * 2_000_001)
        return httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})
    with httpx.Client(transport=httpx.MockTransport(upstream)) as client:
        with pytest.raises(SourceUnavailable) as caught:
            search('clinicaltrials','cancer',10,client=client)
    assert 'sensitive' not in str(caught.value)


def test_bookmarks_persist_project_isolation_and_csrf(workspace):
    client, project = workspace
    saved = client.post('/api/v5.2/bookmarks', json=EVIDENCE)
    assert saved.status_code == 201, saved.text
    record = saved.json()
    assert client.post('/api/v5.2/bookmarks',json=EVIDENCE).json()['id'] == record['id']
    assert client.get('/api/v5.2/bookmarks').json()['items'][0]['evidence'] == EVIDENCE
    with TestClient(create_app(client.app.state.settings)) as another:
        another.cookies.update(client.cookies)
        another.headers['X-Project-ID'] = project['id']
        assert another.get('/api/v5.2/bookmarks').json()['items'][0]['id'] == record['id']
    second = client.post('/api/v5/projects',json={'name':'Other'}).json()
    client.headers['X-Project-ID'] = second['id']
    assert client.get('/api/v5.2/bookmarks').json()['items'] == []
    assert client.delete('/api/v5.2/bookmarks/'+record['id']).status_code == 404
    client.headers['X-Project-ID'] = project['id']
    assert client.post('/api/v5.2/bookmarks',json=EVIDENCE,headers={'Origin':'https://evil.test'}).status_code == 403
    assert client.delete('/api/v5.2/bookmarks/'+record['id']).status_code == 200


@pytest.mark.parametrize('role',['viewer','reviewer','researcher'])
def test_bookmark_project_roles(workspace,role):
    client, project = workspace
    invite = client.post('/api/v5/projects/'+project['id']+'/members',json={'email':role+'@example.org','role':role}).json()
    with TestClient(client.app) as member:
        assert member.post('/api/v5/auth/accept-invite',json={'token':invite['invitation_token'],
                           'password':PASSWORD,'name':role}).status_code == 200
        member.headers['X-Project-ID'] = project['id']
        assert member.get('/api/v5.2/bookmarks').status_code == 200
        expected = 201 if role == 'researcher' else 403
        assert member.post('/api/v5.2/bookmarks',json=EVIDENCE).status_code == expected
        assert member.delete('/api/v5.2/bookmarks/missing').status_code == (404 if role == 'researcher' else 403)


def test_bookmark_rejects_unsafe_citation(workspace):
    client,_ = workspace
    for url in ['javascript:alert(1)','https://evil.test/1234/','https://pubmed.ncbi.nlm.nih.gov/999/']:
        assert client.post('/api/v5.2/bookmarks',json={**EVIDENCE,'url':url}).status_code == 422


def test_email_unconfigured_and_local_are_explicit(workspace,tmp_path):
    client,_ = workspace
    status = client.get('/api/v5.2/account/verification').json()
    assert status['required'] is False and status['delivery_configured'] is False
    assert client.post('/api/v5.2/account/verification/request').status_code == 503
    with TestClient(create_app(configuration(tmp_path/'local').model_copy(update={'auth_mode':'local'}))) as local:
        assert local.get('/api/v5.2/account/verification').json()['available'] is False
        assert local.post('/api/v5.2/account/verification/request').status_code == 503


def test_email_hashed_expiring_single_use_and_required_gate(tmp_path,monkeypatch):
    from backend.app import v52
    delivered = []
    monkeypatch.setattr(v52,'send_verification_email',lambda config,email,token: delivered.append((email,token)))
    cfg = configuration(tmp_path).model_copy(update={'require_email_verification':True,
        'mail_api_key':'test-secret','mail_from':'CTI <test@example.org>','public_base_url':'https://cti.example.org'})
    with TestClient(create_app(cfg)) as client:
        owner(client)
        assert client.get('/api/v5/bootstrap').status_code == 200
        assert client.get('/api/v5/projects').status_code == 403
        sent = client.post('/api/v5.2/account/verification/request')
        assert sent.status_code == 200 and 'test-secret' not in sent.text
        token = delivered[-1][1]
        store = client.app.state.platform_store
        rows = store.execute('SELECT * FROM v52_email_tokens',fetch=True)
        assert token not in str(rows)
        assert client.post('/api/v5.2/auth/verify-email',json={'token':token},headers={'Origin':'https://evil.test'}).status_code == 403
        with TestClient(client.app) as anonymous:
            verified = anonymous.post('/api/v5.2/auth/verify-email',json={'token':token})
            assert verified.status_code == 200 and 'set-cookie' not in verified.headers
            assert anonymous.get('/api/v5/projects').status_code == 401
            assert anonymous.post('/api/v5.2/auth/verify-email',json={'token':token}).status_code == 400
        assert client.get('/api/v5.2/account/verification').json()['verified'] is True
        assert client.post('/api/v5/projects',json={'name':'Verified project'}).status_code == 201
        # A separately minted expired token cannot verify another account.
        store.execute('INSERT INTO v52_email_tokens(token_hash,user_id,expires_at,created_at) VALUES(:hash,:user,:expiry,:created)',
                      {'hash':v52.token_digest('expired-token-1234567890'),'user':rows[0]['user_id'],'expiry':time.time()-1,'created':time.time()-3601})
        assert client.post('/api/v5.2/auth/verify-email',json={'token':'expired-token-1234567890'}).status_code == 400


def test_mail_fixed_resend_host_no_redirect_or_secret_error(monkeypatch,tmp_path):
    from backend.app import v52
    requests=[]
    def upstream(request):
        requests.append(request)
        return httpx.Response(500,json={'error':'test-secret'})
    original = httpx.Client
    monkeypatch.setattr(v52.httpx,'Client',lambda **kw: original(transport=httpx.MockTransport(upstream),**kw))
    cfg = configuration(tmp_path).model_copy(update={'mail_api_key':'test-secret','mail_from':'test@example.org','public_base_url':'https://cti.example.org'})
    with pytest.raises(v52.EmailUnavailable) as caught:
        v52.send_verification_email(cfg,'owner@example.org','a-test-token')
    assert 'test-secret' not in str(caught.value)
    assert str(requests[0].url) == 'https://api.resend.com/emails'
    assert requests[0].headers['Authorization'] == 'Bearer test-secret'


def test_search_endpoint_validates_access_limits_and_safe_failures(workspace,monkeypatch):
    from backend.app import v52
    from backend.app.research_sources import SourceUnavailable
    client, project = workspace
    calls=[]
    def result(source, query, limit):
        calls.append((source,query,limit))
        return {'source':source,'query':query,'items':[EVIDENCE],'total':1,'limit':limit,'retrieved_at':EVIDENCE['retrieved_at']}
    monkeypatch.setattr(v52,'search',result)
    response = client.get('/api/v5.2/research/search',params={'source':'pubmed','q':' cancer ','limit':2})
    assert response.status_code == 200 and response.json()['items'] == [EVIDENCE]
    assert calls == [('pubmed','cancer',2)]
    for params in [{'source':'unknown','q':'cancer'},{'source':'pubmed','q':' '},
                   {'source':'pubmed','q':'x','limit':21},{'source':'pubmed','q':'x'*301}]:
        assert client.get('/api/v5.2/research/search',params=params).status_code == 422
    with TestClient(client.app) as anonymous:
        assert anonymous.get('/api/v5.2/research/search',params={'source':'pubmed','q':'cancer'},headers={'X-Project-ID':project['id']}).status_code == 401
    def unavailable(*args):
        raise SourceUnavailable('PubMed is unavailable. Retry later.')
    monkeypatch.setattr(v52,'search',unavailable)
    response = client.get('/api/v5.2/research/search',params={'source':'pubmed','q':'cancer'})
    assert response.status_code == 503 and response.json()['detail'] == 'PubMed is unavailable. Retry later.'


def test_sources_empty_results_and_result_limit():
    from backend.app.research_sources import search
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(404,json={'error':{'code':'NOT_FOUND','message':'No matches found!'}}))) as client:
        result = search('openfda','absent drug',2,client=client)
    assert result['items'] == [] and result['total'] == 0
    rows=[{'protocolSection':{'identificationModule':{'nctId':'NCT'+str(n).zfill(8),'briefTitle':'Study'}}} for n in range(10)]
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'studies':rows,'totalCount':10}))) as client:
        result = search('clinicaltrials','trial',2,client=client)
    assert len(result['items']) == 2 and result['total'] == 10


def test_mail_success_fragment_and_delivery_failure_cleanup(tmp_path,monkeypatch):
    from backend.app import v52
    import json
    requests=[]
    def upstream(request):
        requests.append(request)
        return httpx.Response(200,json={'id':'mail-id'})
    original = httpx.Client
    monkeypatch.setattr(v52.httpx,'Client',lambda **kw: original(transport=httpx.MockTransport(upstream),**kw))
    cfg = configuration(tmp_path).model_copy(update={'mail_api_key':'test-secret','mail_from':'test@example.org','public_base_url':'https://cti.example.org'})
    v52.send_verification_email(cfg,'owner@example.org','a-test-token')
    payload = json.loads(requests[0].content)
    assert payload['to'] == ['owner@example.org']
    assert 'https://cti.example.org/#verify-email?token=a-test-token' in payload['text']
    monkeypatch.setattr(v52,'send_verification_email',lambda *args: (_ for _ in ()).throw(v52.EmailUnavailable('Email delivery is unavailable.')))
    with TestClient(create_app(cfg)) as client:
        owner(client)
        assert client.post('/api/v5.2/account/verification/request').status_code == 503
        assert client.app.state.platform_store.execute('SELECT * FROM v52_email_tokens',fetch=True) == []


def test_resend_invalidates_older_token_and_mail_rate_limit(tmp_path,monkeypatch):
    from backend.app import v52
    delivered=[]
    monkeypatch.setattr(v52,'send_verification_email',lambda config,email,token:delivered.append(token))
    cfg = configuration(tmp_path).model_copy(update={'mail_api_key':'test-secret','mail_from':'test@example.org','public_base_url':'https://cti.example.org'})
    with TestClient(create_app(cfg)) as client:
        owner(client)
        assert client.post('/api/v5.2/account/verification/request').status_code == 200
        first = delivered[-1]
        assert client.post('/api/v5.2/account/verification/request').status_code == 200
        second = delivered[-1]
        assert first != second
        assert client.post('/api/v5.2/auth/verify-email',json={'token':first}).status_code == 400
        assert client.post('/api/v5.2/account/verification/request').status_code == 200
        assert client.post('/api/v5.2/account/verification/request').status_code == 429
        assert client.post('/api/v5.2/auth/verify-email',json={'token':delivered[-1]}).status_code == 200


def test_verification_config_rejects_unsafe_public_urls_and_local_required(tmp_path):
    for url in ['http://example.org','https://user:password@example.org','https://example.org/?token=x','https://example.org/#token']:
        with pytest.raises(ValueError,match='HTTPS'):
            Settings.model_validate({**configuration(tmp_path).model_dump(),'public_base_url':url})
    with pytest.raises(ValueError,match='AUTH_MODE=session'):
        create_app(configuration(tmp_path).model_copy(update={'auth_mode':'local','require_email_verification':True}))


def test_invalid_verification_input_does_not_echo_token(workspace):
    client,_ = workspace
    secret = 'private-token-' + 'x' * 260
    response = client.post('/api/v5.2/auth/verify-email',json={'token':secret})
    assert response.status_code == 422
    assert secret not in response.text


def test_encoded_html_is_normalized_as_plain_text():
    from backend.app.research_sources import clean_text
    assert clean_text('&lt;b&gt;Trial&lt;/b&gt; &amp; evidence') == 'Trial & evidence'


def test_openfda_unexpected_404_is_unavailable_not_empty_evidence():
    from backend.app.research_sources import search, SourceUnavailable
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(404,json={'error':'upstream routing error'}))) as client:
        with pytest.raises(SourceUnavailable):
            search('openfda','trial',2,client=client)


def test_bookmarks_use_canonical_searched_evidence(workspace):
    client,_ = workspace
    response = client.post('/api/v5.2/bookmarks',json={**EVIDENCE,'title':'Invented claim','summary':'Never returned by PubMed'})
    assert response.status_code == 201
    assert response.json()['evidence'] == EVIDENCE
    client.app.state.platform_store.execute('DELETE FROM v52_evidence_cache')
    duplicate = client.post('/api/v5.2/bookmarks',json={**EVIDENCE,'title':'Different invented claim'})
    assert duplicate.json()['id'] == response.json()['id']
    assert duplicate.json()['evidence'] == EVIDENCE


def test_bookmarks_reject_uncached_future_expired_and_other_project_evidence(workspace):
    client,project = workspace
    assert client.post('/api/v5.2/bookmarks',json={**EVIDENCE,'retrieved_at':'2099-01-01T00:00:00+00:00'}).status_code == 422
    other = client.post('/api/v5/projects',json={'name':'Unsearched'}).json()
    client.headers['X-Project-ID'] = other['id']
    assert client.post('/api/v5.2/bookmarks',json=EVIDENCE).status_code == 422
    client.headers['X-Project-ID'] = project['id']
    client.app.state.platform_store.execute('UPDATE v52_evidence_cache SET expires_at=:expiry',{'expiry':time.time()-1})
    assert client.post('/api/v5.2/bookmarks',json=EVIDENCE).status_code == 422
