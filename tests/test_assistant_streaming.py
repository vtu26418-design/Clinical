"""SSE contracts use chunked fake upstream HTTP; no provider requests are made."""
import asyncio
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from backend.app.main import create_app
from tests.test_v5_platform import config_at, setup, PASSWORD


class Chunks(httpx.AsyncByteStream):
    def __init__(self, frames):
        self.frames = frames
        self.read_count = 0
        self.closed = False

    async def __aiter__(self):
        for frame in self.frames:
            self.read_count += 1
            yield frame.encode()

    async def aclose(self):
        self.closed = True


def frame(payload):
    return 'data: ' + json.dumps(payload) + '\n\n'


def success_frames(provider):
    if provider == 'anthropic':
        return [frame({'type':'message_start','message':{'model':'observed-model'}}),
                frame({'type':'content_block_delta','delta':{'type':'text_delta','text':'Grounded '}}),
                frame({'type':'content_block_delta','delta':{'type':'text_delta','text':'answer'}}),
                frame({'type':'message_delta','delta':{'stop_reason':'end_turn'}}), frame({'type':'message_stop'})]
    if provider == 'openai':
        return [frame({'type':'response.created','response':{'model':'observed-model'}}),
                frame({'type':'response.output_text.delta','delta':'Grounded '}),
                frame({'type':'response.output_text.delta','delta':'answer'}),
                frame({'type':'response.completed','response':{'status':'completed','model':'observed-model','output':[]}})]
    if provider == 'gemini':
        return [frame({'modelVersion':'observed-model','candidates':[{'content':{'parts':[{'text':'Grounded '},{'text':'secret thought','thought':True}]}}]}),
                frame({'candidates':[{'content':{'parts':[{'text':'answer'}]},'finishReason':'STOP'}]})]
    return [frame({'model':'observed-model','choices':[{'delta':{'content':'Grounded '},'finish_reason':None}]}),
            frame({'choices':[{'delta':{'content':'answer'},'finish_reason':None}]}),
            frame({'choices':[{'delta':{},'finish_reason':'stop'}]}), 'data: [DONE]\n\n']


def configured(tmp_path, provider='anthropic'):
    config = config_at(tmp_path)
    setattr(config, provider+'_api_key', 'fixture-secret')
    config.ai_provider = provider
    config.compatible_base_url = 'https://example.test/v1'
    config.compatible_model = 'fixture-model'
    return config


def install_transport(monkeypatch, frames, status=200):
    from backend.app.services import assistant_streaming as streaming
    stream = Chunks(frames)
    requests = []
    def handler(req):
        requests.append(req)
        return httpx.Response(status, stream=stream)
    monkeypatch.setattr(streaming, '_http_client', lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    return stream, requests


def events(body):
    return [(part.split('\n')[0][7:], json.loads(part.split('\n')[1][6:])) for part in body.strip().split('\n\n')]


def conversation(client):
    setup(client)
    project = client.post('/api/v5/projects', json={'name':'Streaming'}).json()
    client.headers['X-Project-ID'] = project['id']
    chat = client.post('/api/v5/conversations', json={}).json()
    return '/api/v5/conversations/'+chat['id'], project


def test_unconfigured_stream_is_json_503_before_headers_without_quota(tmp_path):
    with TestClient(create_app(config_at(tmp_path))) as client:
        path, project = conversation(client)
        response = client.post(path+'/messages/stream', json={'message':'Explain PCI'})
        assert response.status_code == 503
        assert response.headers['content-type'].startswith('application/json')
        assert client.get(path).json()['messages'] == []
        assert client.get('/api/v5/projects/'+project['id']+'/usage').json()['chat_requests_today'] == 0


def test_missing_provider_preserves_dataset_validation_status(tmp_path):
    with TestClient(create_app(config_at(tmp_path))) as client:
        path,_=conversation(client)
        assert client.post(path+'/messages/stream',json={'message':'Explain','dataset_id':'missing'}).status_code == 404


@pytest.mark.parametrize('provider', ['anthropic','openai','gemini','compatible'])
def test_provider_emits_tokens_before_reading_terminal_and_confirms_actual_model(tmp_path, monkeypatch, provider):
    from backend.app.services import assistant_streaming as streaming
    upstream, requests = install_transport(monkeypatch, success_frames(provider))
    async def run():
        generator = streaming.stream_assist(configured(tmp_path, provider), 'Explain', {'text':'x'*50000}, provider)
        first = await anext(generator)
        assert first == {'event':'delta','text':'Grounded '}
        assert upstream.read_count < len(upstream.frames)
        remaining = [item async for item in generator]
        assert remaining[-1]['event'] == 'done'
        result = remaining[-1]['result']
        assert result['reply'] == 'Grounded answer'
        assert result['model'] == 'observed-model'
        assert result['provider_id'] == provider
        assert result['fallback_used'] is False
        assert result['attempted_providers'] == [provider]
    asyncio.run(run())
    assert upstream.closed
    assert len(requests) == 1
    assert len(requests[0].content) < 35000
    assert b'fixture-secret' not in requests[0].content
    hosts = {'anthropic':'api.anthropic.com','openai':'api.openai.com','gemini':'generativelanguage.googleapis.com','compatible':'example.test'}
    assert requests[0].url.host == hosts[provider]
    body = json.loads(requests[0].content)
    if provider == 'gemini':
        assert requests[0].url.path.endswith(':streamGenerateContent')
        assert requests[0].url.params['alt'] == 'sse'
    else:
        assert body['stream'] is True


def test_endpoint_persists_confirmed_reply_and_uses_shared_quota(tmp_path, monkeypatch):
    install_transport(monkeypatch, success_frames('anthropic'))
    with TestClient(create_app(configured(tmp_path))) as client:
        path, project = conversation(client)
        client.put('/api/v5/projects/'+project['id']+'/settings', json={'chat_daily_limit':1})
        response = client.post(path+'/messages/stream', json={'message':'Explain PCI','nct_id':'NCT-SAMPLE-001'})
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/event-stream')
        assert response.headers['cache-control'] == 'no-store'
        parsed = events(response.text)
        assert [name for name, _ in parsed] == ['meta','delta','delta','done']
        assert parsed[0][1]['provider'] == 'Claude'
        assert parsed[0][1]['references'][1]['nct_id'] == 'NCT-SAMPLE-001'
        done = parsed[-1][1]
        assert done['reply'] == 'Grounded answer'
        assert done['messages'][-1]['content'] == done['reply']
        assert all(m['status']=='complete' for m in done['messages'])
        assert client.get(path).json()['messages'] == done['messages']
        assert client.post(path+'/messages',json={'message':'Again'}).status_code == 429
        assert client.app.state.platform_store.one('SELECT busy_until FROM v5_conversations')['busy_until'] == 0


@pytest.mark.parametrize('provider', ['anthropic','openai','gemini','compatible'])
def test_missing_terminal_fails_and_never_persists_partial_reply(tmp_path, monkeypatch, provider):
    frames = success_frames(provider)
    # Each provider must confirm its successful termination, beyond emitted text.
    remove = 2 if provider in {'anthropic','compatible'} else 1
    if provider == 'gemini':
        frames = [frames[0], frame({'candidates':[{'content':{'parts':[{'text':'answer'}]}}]})]
    else:
        frames = frames[:-remove]
    upstream, requests = install_transport(monkeypatch, frames)
    with TestClient(create_app(configured(tmp_path, provider))) as client:
        path, _ = conversation(client)
        parsed = events(client.post(path+'/messages/stream', json={'message':'Explain'}).text)
        assert parsed[-1][0] == 'error'
        assert not any(name == 'done' for name, _ in parsed)
        messages = client.get(path).json()['messages']
        assert len(messages) == 1 and messages[0]['status'] == 'failed'
        assert client.app.state.platform_store.one('SELECT busy_until FROM v5_conversations')['busy_until'] == 0
    assert upstream.closed and len(requests) == 1


@pytest.mark.parametrize('provider,payload', [
    ('anthropic', {'type':'message_delta','delta':{'stop_reason':'refusal'}}),
    ('openai', {'type':'response.refusal.delta','delta':'secret reason'}),
    ('gemini', {'candidates':[{'finishReason':'SAFETY'}]}),
    ('compatible', {'choices':[{'delta':{'refusal':'secret reason'},'finish_reason':'content_filter'}]}),
    ('anthropic', {'type':'error','error':{'message':'fixture-secret internal details'}}),
    ('openai', {'type':'response.incomplete','response':{'status':'incomplete'}}),
])
def test_refusal_and_error_do_not_fallback_or_expose_upstream(tmp_path, monkeypatch, provider, payload):
    _, requests = install_transport(monkeypatch, [frame(payload)])
    cfg = configured(tmp_path, provider)
    cfg.gemini_api_key = cfg.anthropic_api_key = 'fixture-secret'
    with TestClient(create_app(cfg)) as client:
        path, _ = conversation(client)
        body = client.post(path+'/messages/stream', json={'message':'Explain'}).text
        assert events(body)[-1][0] == 'error'
        assert 'fixture-secret' not in body and 'secret reason' not in body
    assert len(requests) == 1


def test_output_bound_errors_instead_of_truncating_and_claiming_success(tmp_path, monkeypatch):
    from backend.app.platform import PROFILES
    from backend.app.services.assistant_service import reply_char_limit
    cap = reply_char_limit({'profile_limits':PROFILES['fast']})
    install_transport(monkeypatch, [frame({'type':'content_block_delta','delta':{'type':'text_delta','text':'x'*(cap+1)}})])
    with TestClient(create_app(configured(tmp_path))) as client:
        path, _ = conversation(client)
        parsed = events(client.post(path+'/messages/stream', json={'message':'Explain','profile':'fast'}).text)
        assert [name for name,_ in parsed] == ['meta','error']
        assert client.get(path).json()['messages'][0]['status'] == 'failed'


def test_stream_protects_owner_project_role_validation_and_busy_gate(tmp_path, monkeypatch):
    _, requests = install_transport(monkeypatch, success_frames('anthropic'))
    with TestClient(create_app(configured(tmp_path))) as client:
        path, project = conversation(client)
        with TestClient(client.app) as anonymous:
            assert anonymous.post(path+'/messages/stream',json={'message':'Explain'}).status_code == 401
        assert client.post(path+'/messages/stream',json={'message':'x'*4001}).status_code == 422
        assert client.post(path+'/messages/stream',json={'message':'Explain','dataset_id':'missing'}).status_code == 404
        token = client.post('/api/v5/projects/'+project['id']+'/members',json={'email':'viewer@example.org','role':'viewer'}).json()['invitation_token']
        with TestClient(client.app) as viewer:
            viewer.post('/api/v5/auth/accept-invite',json={'token':token,'password':PASSWORD,'name':'Viewer'})
            viewer.headers['X-Project-ID'] = project['id']
            assert viewer.post(path+'/messages/stream',json={'message':'Explain'}).status_code == 403
        other = client.post('/api/v5/projects',json={'name':'Other'}).json()
        assert client.post(path+'/messages/stream',json={'message':'Explain'},headers={'X-Project-ID':other['id']}).status_code == 404
        client.app.state.platform_store.execute('UPDATE v5_conversations SET busy_until=:until', {'until':10**12})
        assert client.post(path+'/messages/stream',json={'message':'Explain'}).status_code == 409
    assert requests == []


def test_persistence_failure_rolls_back_final_reply_and_releases_busy(tmp_path, monkeypatch):
    install_transport(monkeypatch, success_frames('anthropic'))
    with TestClient(create_app(configured(tmp_path))) as client:
        path, _ = conversation(client)
        store = client.app.state.platform_store
        def fail_assistant_insert(conn, cursor, statement, parameters, context, executemany):
            if statement.startswith('INSERT INTO v5_messages') and "'assistant'" in statement:
                raise RuntimeError('fixture-secret database details')
        event.listen(store.engine, 'before_cursor_execute', fail_assistant_insert)
        parsed = events(client.post(path+'/messages/stream',json={'message':'Explain'}).text)
        assert parsed[-1][0] == 'error'
        assert 'fixture-secret' not in json.dumps(parsed)
        assert client.get(path).json()['messages'][0]['status'] == 'failed'
        assert len(client.get(path).json()['messages']) == 1
        assert store.one('SELECT busy_until FROM v5_conversations')['busy_until'] == 0


def test_disconnect_closes_upstream_and_marks_failed_without_waiting_for_next_token(tmp_path, monkeypatch):
    from backend.app.services import assistant_streaming as streaming
    class Blocked(Chunks):
        async def __aiter__(self):
            yield frame({'type':'content_block_delta','delta':{'type':'text_delta','text':'Partial'}}).encode()
            await asyncio.Event().wait()
    upstream = Blocked([])
    monkeypatch.setattr(streaming,'_http_client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,stream=upstream))))
    with TestClient(create_app(configured(tmp_path))) as client:
        path, _ = conversation(client)
        endpoint = next(route.endpoint for route in client.app.routes if getattr(route,'path','') == '/api/v5/conversations/{identifier}/messages/stream')
        from starlette.requests import Request
        from backend.app.platform import MessageInput
        request = Request({'type':'http','headers':[(b'cookie', ('cti_session='+client.cookies.get('cti_session')).encode()),(b'x-project-id',client.headers['X-Project-ID'].encode())]})
        response = endpoint(path.rsplit('/',1)[-1], MessageInput(message='Explain'), request)
        async def run():
            disconnect = asyncio.Event()
            async def send(message):
                if b'Partial' in message.get('body',b''):
                    disconnect.set()
            async def receive():
                await disconnect.wait()
                return {'type':'http.disconnect'}
            await asyncio.wait_for(response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send), 1)
        asyncio.run(run())
        assert upstream.closed
        assert client.get(path).json()['messages'][0]['status'] == 'failed'
        assert client.app.state.platform_store.one('SELECT busy_until FROM v5_conversations')['busy_until'] == 0


@pytest.mark.parametrize('provider,payload', [
    ('anthropic', {'type':'message_delta','delta':{'stop_reason':'max_tokens'}}),
    ('openai', {'type':'response.completed','response':{'status':'incomplete','output':[]}}),
    ('gemini', {'candidates':[{'finishReason':'MAX_TOKENS'}]}),
    ('compatible', {'choices':[{'delta':{},'finish_reason':'length'}]}),
])
def test_truncated_finish_reason_is_failure(tmp_path, monkeypatch, provider, payload):
    from backend.app.services import assistant_streaming as streaming
    from backend.app.services.assistant_service import AssistantUnavailable
    _, requests = install_transport(monkeypatch,[success_frames(provider)[0],frame(payload)])
    async def run():
        with pytest.raises(AssistantUnavailable,match='complete reply'):
            _ = [item async for item in streaming.stream_assist(configured(tmp_path,provider),'Explain',{},provider)]
    asyncio.run(run())
    assert len(requests) == 1


def test_arbitrary_network_chunk_boundaries_preserve_unicode_and_multiline_data(tmp_path, monkeypatch):
    from backend.app.services import assistant_streaming as streaming
    payload = 'data: {"type":"content_block_delta",\r\ndata: "delta":{"type":"text_delta","text":"研究\\nanswer"}}\r\n\r\n'
    raw = (payload + ''.join(success_frames('anthropic')[-2:])).encode()
    class ByteChunks(Chunks):
        async def __aiter__(self):
            for byte in raw:
                yield bytes([byte])
    upstream = ByteChunks([])
    monkeypatch.setattr(streaming,'_http_client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,stream=upstream))))
    async def run():
        result = [item async for item in streaming.stream_assist(configured(tmp_path),'Explain',{},'anthropic')]
        assert result[0]['text'] == '研究\nanswer'
        assert result[-1]['result']['reply'] == '研究\nanswer'
    asyncio.run(run())
    assert upstream.closed


@pytest.mark.parametrize('raw', ['data: '+ 'x'*65537+'\n\n', 'data: {not json}\n\n', 'data: [DONE]\n\n'],ids=['oversized','malformed','unexpected_done'])
def test_malformed_or_oversized_events_fail_safely(tmp_path,monkeypatch,raw):
    from backend.app.services import assistant_streaming as streaming
    from backend.app.services.assistant_service import AssistantUnavailable
    install_transport(monkeypatch,[raw])
    async def run():
        with pytest.raises(AssistantUnavailable):
            _ = [item async for item in streaming.stream_assist(configured(tmp_path),'Explain',{},'anthropic')]
    asyncio.run(run())


def test_disconnect_before_body_iteration_cleans_reserved_message_and_lock(tmp_path,monkeypatch):
    _, requests = install_transport(monkeypatch,success_frames('anthropic'))
    with TestClient(create_app(configured(tmp_path))) as client:
        path, _ = conversation(client)
        endpoint = next(route.endpoint for route in client.app.routes if getattr(route,'path','') == '/api/v5/conversations/{identifier}/messages/stream')
        from starlette.requests import Request
        from backend.app.platform import MessageInput
        request = Request({'type':'http','headers':[(b'cookie', ('cti_session='+client.cookies.get('cti_session')).encode()),(b'x-project-id',client.headers['X-Project-ID'].encode())]})
        response = endpoint(path.rsplit('/',1)[-1],MessageInput(message='Explain'),request)
        async def run():
            async def send(message):
                # The socket fails before the body generator is first entered.
                raise OSError('socket closed')
            async def receive():
                await asyncio.Event().wait()
            with pytest.raises(OSError):
                await response({'type':'http','asgi':{'spec_version':'2.4'}},receive,send)
        asyncio.run(run())
        assert client.get(path).json()['messages'][0]['status'] == 'failed'
        assert client.app.state.platform_store.one('SELECT busy_until FROM v5_conversations')['busy_until'] == 0
    assert requests == []


@pytest.mark.parametrize('status',[401,429,503])
def test_upstream_http_failures_remain_one_provider_and_release_busy(tmp_path,monkeypatch,status):
    _, requests = install_transport(monkeypatch,[frame({'error':'fixture-secret'})],status=status)
    cfg=configured(tmp_path)
    cfg.gemini_api_key='fixture-secret'
    with TestClient(create_app(cfg)) as client:
        path,_=conversation(client)
        parsed=events(client.post(path+'/messages/stream',json={'message':'Explain'}).text)
        assert parsed[-1][0]=='error'
        assert 'fixture-secret' not in json.dumps(parsed)
        assert client.get(path).json()['messages'][0]['status']=='failed'
        assert client.app.state.platform_store.one('SELECT busy_until FROM v5_conversations')['busy_until']==0
    assert len(requests)==1


def test_total_deadline_cancels_stalled_provider_and_marks_failed(tmp_path,monkeypatch):
    from backend.app.services import assistant_streaming as streaming
    class Blocked(Chunks):
        async def __aiter__(self):
            await asyncio.Event().wait()
            yield b''
    upstream=Blocked([])
    monkeypatch.setattr(streaming,'STREAM_TIMEOUT_SECONDS',.01,raising=False)
    monkeypatch.setattr(streaming,'_http_client',lambda:httpx.AsyncClient(transport=httpx.MockTransport(lambda req:httpx.Response(200,stream=upstream))))
    async def run():
        from backend.app.services.assistant_service import AssistantUnavailable
        with pytest.raises(AssistantUnavailable,match='time limit'):
            _=[item async for item in streaming.stream_assist(configured(tmp_path),'Explain',{},'anthropic')]
    # The outer guard makes the initial red run deterministic rather than hang.
    asyncio.run(asyncio.wait_for(run(),.3))
    assert upstream.closed
    with TestClient(create_app(configured(tmp_path))) as client:
        path,_=conversation(client)
        parsed=events(client.post(path+'/messages/stream',json={'message':'Explain'}).text)
        assert parsed[-1][0]=='error' and 'time limit' in parsed[-1][1]['message']
        assert client.get(path).json()['messages'][0]['status']=='failed'
        assert client.app.state.platform_store.one('SELECT busy_until FROM v5_conversations')['busy_until']==0
