"""Grounding and reviewed feedback contracts; providers are never contacted."""
import json
import os

import pytest
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.services import assistant_service
from tests.test_v5_platform import PASSWORD, TOKEN, setup


@pytest.fixture
def assistant_owner(tmp_path, monkeypatch):
    source = os.environ.get('TEST_DATABASE_URL')
    if not source:
        pytest.fail('TEST_DATABASE_URL is required for PostgreSQL assistant tests.')
    config = Settings(_env_file=None, database_url=source,
                      storage_dir=str(tmp_path), auth_mode='session', setup_token=TOKEN,
                      openai_api_key='', gemini_api_key='', anthropic_api_key='', compatible_api_key='')
    app = create_app(config)
    seen = []
    def reply(config, message, context, provider=None):
        seen.append(context)
        return {'reply':'The selected sample is a software fixture [S1].', 'provider':'Stub',
                'provider_id':'stub', 'model':'stub', 'attempted_providers':['stub'], 'fallback_used':False}
    monkeypatch.setattr(assistant_service, 'assist', reply)
    try:
        with TestClient(app) as client:
            setup(client)
            project = client.post('/api/v5/projects', json={'name':'Assistant evidence'}).json()
            client.headers['X-Project-ID'] = project['id']
            yield client, project, seen
    finally:
        app.state.platform_store.engine.dispose()


def completed_message(client):
    chat = client.post('/api/v5/conversations', json={'title':'Grounding'}).json()
    response = client.post('/api/v5/conversations/' + chat['id'] + '/messages',
                           json={'message':'Explain PCI', 'dataset_id':'sample-fixture', 'nct_id':'NCT-SAMPLE-001'})
    assert response.status_code == 200, response.text
    messages = response.json()['messages']
    return chat, messages[-1], messages[-2]


def test_feedback_requires_actual_complete_assistant_and_owner_scope(assistant_owner):
    client, project, _ = assistant_owner
    chat, answer, question = completed_message(client)
    payload = {'rating':2, 'comment':'Explain why PCI is descriptive.', 'dataset_id':'sample-fixture'}
    for identifier in ('0' * 32, question['id']):
        assert client.post('/api/v5/messages/' + identifier + '/feedback', json=payload).status_code == 404
    path = '/api/v5/messages/' + answer['id'] + '/feedback'
    assert client.post(path, json={**payload, 'dataset_id':'another-dataset'}).status_code == 422
    saved = client.post(path, json=payload)
    assert saved.status_code == 200, saved.text
    record = saved.json()['feedback']
    assert record['project_id'] == project['id'] and record['conversation_id'] == chat['id']
    assert record['message_id'] == answer['id'] and record['review_status'] == 'pending'
    assert client.post(path, json={**payload, 'rating':4}).json()['feedback']['id'] == record['id']
    second = client.post('/api/v5/projects', json={'name':'Unrelated'}).json()
    client.headers['X-Project-ID'] = second['id']
    assert client.post(path, json=payload).status_code == 404
    client.headers['X-Project-ID'] = project['id']
    invite = client.post('/api/v5/projects/' + project['id'] + '/members',
                         json={'email':'assistant-reviewer@example.org', 'role':'reviewer'}).json()
    with TestClient(client.app) as reviewer:
        assert reviewer.post('/api/v5/auth/accept-invite', json={'token':invite['invitation_token'], 'password':PASSWORD, 'name':'Reviewer'}).status_code == 200
        reviewer.headers['X-Project-ID'] = project['id']
        assert reviewer.post(path, json=payload).status_code == 404
        assert reviewer.get('/api/v5/projects/' + project['id'] + '/assistant-feedback').status_code == 403
    assert not list(client.app.state.settings.store_path.rglob('feedback/*.json'))


def test_only_owner_reviewed_project_corrections_reach_prompts(assistant_owner):
    from backend.app.services.assistant_feedback import get_reviewed_feedback_context
    client, project, seen = assistant_owner
    _, answer, _ = completed_message(client)
    submitted = client.post('/api/v5/messages/' + answer['id'] + '/feedback',
                            json={'rating':2, 'comment':'Unreviewed text must never instruct the model.'}).json()['feedback']
    store = client.app.state.platform_store
    assert get_reviewed_feedback_context(store, project['id'], 'sample-fixture') == []
    route = '/api/v5/projects/' + project['id'] + '/assistant-feedback'
    assert client.get(route).json()['items'][0]['id'] == submitted['id']
    assert client.put(route + '/' + submitted['id'], json={'status':'approved', 'correction':''}).status_code == 422
    correction = 'PCI describes protocol complexity; it is not a probability of success.'
    reviewed = client.put(route + '/' + submitted['id'], json={'status':'approved', 'correction':correction})
    assert reviewed.status_code == 200, reviewed.text
    assert get_reviewed_feedback_context(store, project['id'], 'other-dataset') == []
    completed_message(client)
    assert seen[-1]['reviewed_corrections'][0]['correction'] == correction
    assert seen[-1]['reviewed_corrections'][0]['reference_id'] in {ref['reference_id'] for ref in seen[-1]['sources']}
    assert 'Unreviewed text' not in json.dumps(seen[-1])
    other = client.post('/api/v5/projects', json={'name':'Other'}).json()
    assert get_reviewed_feedback_context(store, other['id'], 'sample-fixture') == []
    assert client.delete('/api/v5/conversations/' + submitted['conversation_id']).status_code == 200
    assert get_reviewed_feedback_context(store, project['id'], 'sample-fixture') == []


def test_grounding_contains_exact_cohort_sources_models_and_missing_evidence(assistant_owner):
    client, _, seen = assistant_owner
    completed_message(client)
    context = seen[-1]
    assert context['cohort']['row_count'] == context['dataset']['row_count']
    assert context['cohort']['scope'] == 'full_dataset'
    assert context['selected_study']['nct_id'] == 'NCT-SAMPLE-001'
    assert context['sources'][0]['reference_id'] == 'S1'
    assert all(item.get('reference_id') for item in context['sources'])
    assert any('prediction' in entry.lower() for entry in context['missing_evidence'])
    assert 'active_models' in context


def test_zero_daily_quota_still_counts_completed_requests(assistant_owner):
    client, project, _ = assistant_owner
    route = '/api/v5/projects/' + project['id']
    response = client.put(route + '/settings', json={'chat_daily_limit':0, 'chat_max_output_tokens':12000, 'chat_context_chars':100000})
    assert response.status_code == 200, response.text
    completed_message(client)
    completed_message(client)
    usage = client.get(route + '/usage').json()
    assert usage['chat_daily_limit'] == 0 and usage['chat_requests_today'] == 2


def test_route_rejects_adapter_overflow_without_persisting_truncated_success(assistant_owner, monkeypatch):
    client, _, _ = assistant_owner
    chat = client.post('/api/v5/conversations', json={}).json()
    monkeypatch.setattr(assistant_service, 'assist', lambda config,message,context,provider=None:
                        {'reply':'x' * (assistant_service.reply_char_limit(context) + 1)})
    response = client.post('/api/v5/conversations/' + chat['id'] + '/messages', json={'message':'Explain','profile':'fast'})
    assert response.status_code == 503, response.text
    messages = client.get('/api/v5/conversations/' + chat['id']).json()['messages']
    assert messages[-1]['role'] == 'user' and messages[-1]['status'] == 'failed'
    assert not any(message['role'] == 'assistant' for message in messages)


def test_budgeted_prompt_keeps_valid_json_and_exact_source_selection():
    from types import SimpleNamespace
    config = SimpleNamespace(ai_max_output_tokens=16000, ai_context_chars=120000)
    limits = assistant_service.resolve_profile_limits(config, {'chat_max_output_tokens':9000, 'chat_context_chars':5000},
                                                     {'max_output_tokens':16000, 'context_chars':120000, 'history_messages':30})
    assert limits == {'max_output_tokens':9000, 'context_chars':5000, 'history_messages':30}
    context = {'profile_limits':limits, 'selected_study':{'enrollment':37, 'brief_summary':'x' * 20000},
               'history':[{'role':'user', 'content':'h' * 5000}], 'sources':[{'reference_id':'S1', 'kind':'study'}]}
    prompt, selected = assistant_service.build_prompt(config, 'Question', context)
    data = json.loads(prompt.split('Evidence JSON:\n', 1)[1])
    assert data['selected_study']['enrollment'] == 37
    assert len(json.dumps(data, ensure_ascii=False)) <= 5000
    assert data['context_selection']['omitted']
    repeated_prompt, _ = assistant_service.build_prompt(config, 'Question', data)
    repeated = json.loads(repeated_prompt.split('Evidence JSON:\n', 1)[1])
    assert repeated['context_selection']['omitted'] == data['context_selection']['omitted']
    assert selected['max_output_tokens'] == 9000
    assert assistant_service.reply_char_limit(context) > 20000


def test_context_omission_removes_the_exact_protocol_section_reference():
    context = {'project_documents':[
        {'document_id':'doc','page':1,'section':'A','text':'a' * 1500},
        {'document_id':'doc','page':1,'section':'B','text':'b' * 1500}],
        'sources':[
        {'reference_id':'S1','kind':'document','document_id':'doc','page':1,'section':'A'},
        {'reference_id':'S2','kind':'document','document_id':'doc','page':1,'section':'B'}]}
    selected = assistant_service.select_context(context, 2000)
    assert [item['section'] for item in selected['project_documents']] == ['A']
    assert [source['reference_id'] for source in selected['sources']] == ['S1']
    assert context['project_documents'][1]['text'] == 'b' * 1500


def test_provider_output_budget_over_legacy_cap(monkeypatch):
    config = Settings(_env_file=None, ai_max_output_tokens=16000, anthropic_api_key='stub',
                      openai_api_key='', gemini_api_key='', compatible_api_key='')
    captured = []
    def call(config, provider, prompt, tokens):
        captured.append(tokens)
        return 'a' * 25000, 'observed'
    monkeypatch.setattr(assistant_service, '_call', call)
    result = assistant_service.assist(config, 'Explain', {'profile_limits':{'max_output_tokens':9000, 'context_chars':60000}})
    assert captured == [9000] and len(result['reply']) == 25000


def test_unknown_inline_source_cannot_be_saved_as_grounded_answer(monkeypatch):
    config = Settings(_env_file=None, anthropic_api_key='stub', openai_api_key='', gemini_api_key='', compatible_api_key='')
    monkeypatch.setattr(assistant_service, '_call', lambda *args: ('Invented reference [S9]', 'stub'))
    with pytest.raises(assistant_service.AssistantUnavailable, match='source'):
        assistant_service.assist(config, 'Explain', {'sources':[{'reference_id':'S1','kind':'dataset'}]})


@pytest.mark.parametrize('provider,payload', [
    ('anthropic', {'stop_reason':'max_tokens','content':[{'type':'text','text':'Partial answer'}]}),
    ('gemini', {'candidates':[{'finishReason':'MAX_TOKENS','content':{'parts':[{'text':'Partial answer'}]}}]}),
    ('compatible', {'choices':[{'finish_reason':'length','message':{'content':'Partial answer'}}]}),
])
def test_nonstream_token_exhaustion_does_not_save_partial_or_contact_fallback(monkeypatch, provider, payload):
    config = Settings(_env_file=None, anthropic_api_key='stub-a', gemini_api_key='stub-g',
                      compatible_api_key='stub-c', compatible_base_url='https://example.test/v1',
                      compatible_model='stub', ai_provider_priority=provider + ',anthropic,gemini,compatible')
    calls = []
    monkeypatch.setattr(assistant_service, '_post', lambda *args: calls.append(args[0]) or payload)
    with pytest.raises(assistant_service.AssistantUnavailable, match='token budget'):
        assistant_service.assist(config, 'Explain', {})
    assert len(calls) == 1


def test_actual_saved_inference_and_protocol_are_citable_with_exact_provenance(assistant_owner):
    client, project, seen = assistant_owner
    starter = client.post('/api/v1/datasets/starter')
    assert starter.status_code == 201, starter.text
    data = starter.json()
    registry = client.app.state.project_registry(project['id'])
    study = registry.frame(data['id']).iloc[0].to_dict()
    inferred = client.post('/api/v5/inference/batch', json={'dataset_id':data['id'],'limit':1})
    assert inferred.status_code == 201, inferred.text
    prediction = inferred.json()
    protocol = client.post('/api/v5/protocols/text', json={'title':'Source test excerpt',
                             'text':'Software test excerpt\nTarget enrollment: ' + str(int(study['enrollment'])) + ' participants\nPrimary endpoint: software extraction check.'})
    assert protocol.status_code == 201, protocol.text
    chat = client.post('/api/v5/conversations', json={}).json()
    response = client.post('/api/v5/conversations/' + chat['id'] + '/messages',
                           json={'message':'Explain enrollment and protocol complexity with saved prediction evidence',
                                 'dataset_id':data['id'],'nct_id':study['nct_id']})
    assert response.status_code == 200, response.text
    context = seen[-1]
    saved = context['saved_predictions'][0]
    assert saved['items'] == prediction['items']
    assert saved['model']['artifact_sha256'] == prediction['model']['artifact_sha256']
    assert saved['dataset']['sha256'] == data['sha256']
    assert context['project_documents']
    reference_ids = {ref['reference_id'] for ref in response.json()['references']}
    assert saved['reference_id'] in reference_ids
    assert all(item['reference_id'] in reference_ids for item in context['project_documents'])
    assert all(item['reference_id'] in reference_ids for item in context['active_models'])


def test_grounding_preserves_missing_phase_status_sentinels():
    import pandas as pd
    from backend.app.assistant_v5202 import _cohort_context
    class Registry:
        def frame(self, identifier):
            return pd.DataFrame({'phase':['Not reported','PHASE1'], 'status':['Unknown','COMPLETED']})
    context = _cohort_context(Registry(), 'software-only', {'is_fixture':True})
    assert context['missingness'] == {'phase':1,'status':1}


def test_local_feedback_requires_a_real_account(tmp_path):
    config = Settings(_env_file=None, storage_dir=str(tmp_path), auth_mode='local')
    app = create_app(config)
    try:
        with TestClient(app) as client:
            response = client.post('/api/v5/messages/'+'0'*32+'/feedback',json={'rating':2})
            assert response.status_code == 403
            assert 'authenticated account' in response.json()['detail']
    finally:
        app.state.platform_store.engine.dispose()
