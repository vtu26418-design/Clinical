"""Provider contracts are tested with controlled HTTP responses, never real keys."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.main import create_research_app as create_app
from backend.app.services import assistant_service as service


def config(**values):
    return Settings(_env_file=None, openai_api_key='', gemini_api_key='',
                    anthropic_api_key='', compatible_api_key='', **values)


@pytest.mark.parametrize('provider,field', [('openai', 'openai_api_key'), ('gemini', 'gemini_api_key'), ('anthropic', 'anthropic_api_key')])
def test_auto_uses_only_configured_key(provider, field):
    c = config()
    setattr(c, field, 'fixture-secret')
    assert service.provider_candidates(c) == [provider]
    status = service.assistant_status(c)
    assert status['selected_provider'] == provider
    assert status['enabled']
    assert 'fixture-secret' not in json.dumps(status)


def test_auto_priority_and_manual_override():
    c = config()
    c.openai_api_key = c.gemini_api_key = c.anthropic_api_key = 'fixture-secret'
    assert service.provider_candidates(c) == ['openai', 'anthropic', 'gemini']
    c.ai_provider_priority = 'gemini,claude,openai,compatible'
    assert service.provider_candidates(c) == ['gemini', 'anthropic', 'openai']
    assert service.provider_candidates(c, 'openai') == ['openai']
    c.ai_provider = 'anthropic'
    assert service.provider_candidates(c) == ['anthropic']


def test_no_key_or_unconfigured_manual_choice():
    c = config()
    assert not service.assistant_status(c)['enabled']
    with pytest.raises(service.AssistantUnavailable, match='configured'):
        service.assist(c, 'Explain', {})
    c.gemini_api_key = 'fixture'
    with pytest.raises(service.AssistantUnavailable, match='OpenAI'):
        service.assist(c, 'Explain', {}, 'openai')


@pytest.mark.parametrize('provider', ['gemini', 'anthropic', 'compatible'])
def test_native_wire_format_bounded_context_and_actual_provider(provider, monkeypatch):
    c = config(compatible_base_url='https://example.test/v1', compatible_model='custom-model')
    setattr(c, {'gemini':'gemini_api_key','anthropic':'anthropic_api_key','compatible':'compatible_api_key'}[provider], 'fixture-secret')
    requests = []
    def handle(req):
        requests.append(req)
        body = json.loads(req.content)
        assert 'fixture-secret' not in req.url.query.decode()
        assert 'fixture-secret' not in req.content.decode()
        assert len(req.content) < 30000
        if provider == 'gemini':
            assert req.headers['x-goog-api-key'] == 'fixture-secret'
            assert req.url.host == 'generativelanguage.googleapis.com'
            assert body['systemInstruction']['parts'][0]['text'] == service.INSTRUCTIONS
            assert body['contents'][0]['role'] == 'user'
            return httpx.Response(200, json={'modelVersion':'gemini-observed','candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'private thought','thought':True},{'text':'Grounded answer'}]}}]})
        if provider == 'anthropic':
            assert req.headers['x-api-key'] == 'fixture-secret'
            assert req.headers['anthropic-version'] == '2023-06-01'
            assert body['system'] == service.INSTRUCTIONS
            assert body['max_tokens'] == 700
            return httpx.Response(200, json={'model':'claude-observed','content':[{'type':'thinking','thinking':'private thought'},{'type':'text','text':'Grounded answer'}]})
        assert req.headers['authorization'] == 'Bearer fixture-secret'
        assert str(req.url) == 'https://example.test/v1/chat/completions'
        assert body['messages'][0]['role'] == 'system'
        return httpx.Response(200, json={'model':'custom-observed','choices':[{'message':{'content':'Grounded answer'}}]})
    monkeypatch.setattr(service, '_http_client', lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    r = service.assist(c, 'Explain', {'text':'x'*50000})
    assert r['reply'] == 'Grounded answer'
    assert r['provider_id'] == provider
    assert r['model'].endswith('-observed')
    assert r['fallback_used'] is False
    assert len(requests) == 1


@pytest.mark.parametrize('status', [401,403,404,408,429,500,503,529])
def test_auto_falls_back_after_access_or_transient_failure(status, monkeypatch):
    c = config()
    c.anthropic_api_key = 'secret-a'
    c.gemini_api_key = 'secret-g'
    seen = []
    def handle(req):
        seen.append(req.url.host)
        if req.url.host == 'api.anthropic.com':
            return httpx.Response(status, json={'error':{'message':'do not expose secret-a'}})
        return httpx.Response(200, json={'candidates':[{'content':{'parts':[{'text':'Fallback answer'}]}}]})
    monkeypatch.setattr(service, '_http_client', lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    result = service.assist(c, 'Explain', {})
    assert result['provider_id'] == 'gemini'
    assert result['fallback_used']
    assert result['attempted_providers'] == ['anthropic','gemini']
    assert len(seen) == 2
    assert 'secret-a' not in json.dumps(result)


def test_timeout_falls_back(monkeypatch):
    c = config(); c.anthropic_api_key='a'; c.gemini_api_key='g'
    def handle(req):
        if req.url.host == 'api.anthropic.com':
            raise httpx.ReadTimeout('secret-a', request=req)
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'OK'}]}}]})
    monkeypatch.setattr(service,'_http_client',lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    assert service.assist(c,'Explain',{})['provider_id'] == 'gemini'


@pytest.mark.parametrize('payload,status', [({'error':{'message':'secret-a'}},400), ({'content':[]},200), ({'stop_reason':'refusal','content':[{'type':'text','text':'Refused'}]},200)])
def test_never_falls_back_for_bad_request_empty_output_or_refusal(payload,status,monkeypatch):
    c=config();c.anthropic_api_key='secret-a';c.gemini_api_key='secret-g';seen=[]
    def handle(req):
        seen.append(req.url.host)
        return httpx.Response(status,json=payload)
    monkeypatch.setattr(service,'_http_client',lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    with pytest.raises(service.AssistantUnavailable) as err:service.assist(c,'Explain',{})
    assert len(seen)==1
    assert 'secret-a' not in str(err.value)


def test_manual_and_disabled_fallback_do_not_switch(monkeypatch):
    c=config();c.anthropic_api_key='a';c.gemini_api_key='g';seen=[]
    def handle(req):seen.append(req.url.host);return httpx.Response(429,json={})
    monkeypatch.setattr(service,'_http_client',lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    with pytest.raises(service.AssistantUnavailable):service.assist(c,'Explain',{},'anthropic')
    assert len(seen)==1
    c.ai_auto_fallback=False
    with pytest.raises(service.AssistantUnavailable):service.assist(c,'Explain',{})
    assert len(seen)==2


@pytest.mark.parametrize('url', ['http://example.test/v1','https://user:password@example.test/v1','https://example.test/v1?key=secret','https://example.test/v1#x'])
def test_custom_endpoint_requires_clean_https(url):
    with pytest.raises(ValidationError):config(compatible_base_url=url)


def test_gemini_blocked_response_is_not_rerouted(monkeypatch):
    c=config(ai_provider_priority='gemini,openai,anthropic,compatible');c.gemini_api_key='g';c.anthropic_api_key='a';seen=[]
    def handle(req):seen.append(req);return httpx.Response(200,json={'promptFeedback':{'blockReason':'SAFETY'}})
    monkeypatch.setattr(service,'_http_client',lambda: httpx.Client(transport=httpx.MockTransport(handle)))
    with pytest.raises(service.AssistantUnavailable,match='declined'):service.assist(c,'Explain',{})
    assert len(seen)==1


def test_api_health_single_gemini_and_request_selection(tmp_path,monkeypatch):
    c=config(storage_dir=str(tmp_path),database_url='',api_bearer_token='');c.gemini_api_key='secret-g'
    monkeypatch.setattr(service,'_http_client',lambda: httpx.Client(transport=httpx.MockTransport(lambda req:httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'OK'}]}}]}))))
    with TestClient(create_app(c)) as client:
        health=client.get('/api/v1/health')
        assert health.json()['assistant_enabled'] is True
        assert health.json()['openai_configured'] is False
        assert health.json()['assistant']['selected_provider']=='gemini'
        assert 'secret-g' not in health.text
        result=client.post('/api/v1/assistant',json={'message':'Explain','provider':'gemini'})
        assert result.status_code==200
        assert result.json()['provider_id']=='gemini'
        assert client.post('/api/v1/assistant',json={'message':'Explain','provider':'invalid'}).status_code==422

