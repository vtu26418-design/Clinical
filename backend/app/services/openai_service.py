"""Compatibility import for callers of the original OpenAI-only helper."""
from .assistant_service import AssistantUnavailable, assist as _assist

def assist(config, message, context) -> str:
    return _assist(config, message, context, provider='openai')['reply']
