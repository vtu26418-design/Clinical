"""v5.2.0.3 bounds and answer policy; no provider credentials or network calls."""
from types import SimpleNamespace
import json

import pytest
from pydantic import ValidationError
from sqlalchemy import text

from backend.app.platform import DEFAULT_SETTINGS, MessageInput
from backend.app.services import assistant_service
from tests.test_v5_platform import owner


def test_message_accepts_full_32768_character_question_without_prompt_truncation():
    message = 'q' * 32760 + 'THE_END!'
    assert MessageInput(message=message).message == message
    prompt, limits = assistant_service.build_prompt(
        SimpleNamespace(ai_context_chars=2000, ai_max_output_tokens=100), message,
        {'profile_limits': {'context_chars': 2000, 'max_output_tokens': 100}})
    assert message in prompt
    assert limits['context_chars'] == 2000 and limits['max_output_tokens'] == 100
    with pytest.raises(ValidationError):
        MessageInput(message=message + 'x')
    with pytest.raises(ValidationError):
        MessageInput(message='   ')


def test_new_projects_have_no_daily_application_quota(owner):
    client, project = owner
    assert DEFAULT_SETTINGS['chat_daily_limit'] == 0
    assert project['settings']['chat_daily_limit'] == 0
    route = '/api/v5/projects/' + project['id'] + '/settings'
    assert client.put(route, json={'chat_daily_limit': 7}).status_code == 200
    assert client.get('/api/v5/bootstrap').json()['projects'][0]['settings']['chat_daily_limit'] == 7


def test_general_answer_policy_separates_project_facts_and_preserves_invalid_source_rejection():
    policy = assistant_service.INSTRUCTIONS.lower()
    assert 'general questions' in policy and 'general knowledge' in policy
    assert 'project-specific' in policy and 'provided' in policy
    assert 'never invent' in policy and 'clinical' in policy
    prompt, _ = assistant_service.build_prompt(SimpleNamespace(ai_context_chars=2000, ai_max_output_tokens=100),
                                               'Explain a Python list.', {})
    assert 'general questions' in prompt and 'project-specific claims' in prompt
    assistant_service.validate_reply_sources('Here is a general explanation without project claims.', {'sources': []})
    with pytest.raises(assistant_service.AssistantUnavailable):
        assistant_service.validate_reply_sources('An invented project result [S9].', {'sources': []})


def test_existing_project_with_omitted_quota_keeps_legacy_default_without_migration(owner):
    client, project = owner
    store = client.app.state.platform_store
    old_settings = {'default_profile': 'fast', 'chat_max_output_tokens': 400}
    with store.transaction() as conn:
        conn.execute(text('UPDATE v5_projects SET settings=:settings WHERE id=:id'),
                     {'settings': json.dumps(old_settings), 'id': project['id']})
    loaded = client.get('/api/v5/bootstrap').json()['projects'][0]['settings']
    assert loaded['chat_daily_limit'] == 50
    assert loaded['chat_max_output_tokens'] == 400
    assert json.loads(store.one('SELECT settings FROM v5_projects WHERE id=:id', {'id':project['id']})['settings']) == old_settings


def test_prompt_rejects_oversize_direct_call_and_preserves_provider_budget():
    config = SimpleNamespace(ai_context_chars=2000, ai_max_output_tokens=100)
    with pytest.raises(assistant_service.AssistantUnavailable):
        assistant_service.build_prompt(config, 'q' * 32769, {})
    limits = assistant_service.resolve_profile_limits(config, {'chat_daily_limit':0},
                                                     {'context_chars':120000, 'max_output_tokens':16000})
    assert limits == {'context_chars':2000, 'max_output_tokens':100}
