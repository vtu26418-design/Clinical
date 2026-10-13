"""Native provider token streams with explicit completion and bounded SSE parsing."""
from __future__ import annotations

import asyncio
import json
import time
from urllib.parse import quote

import anyio
import httpx
from starlette.responses import StreamingResponse

from .assistant_service import (
    AssistantUnavailable, INSTRUCTIONS, PROVIDERS, _key, _model, _status_failure,
    build_prompt, provider_candidates, reply_char_limit, select_context, validate_reply_sources,
)

MAX_WIRE_BYTES = 1_000_000
MAX_FRAME_BYTES = 65536
STREAM_TIMEOUT_SECONDS = 120


def select_provider(config, requested=None):
    candidates = provider_candidates(config, requested)
    if not candidates:
        raise AssistantUnavailable('The selected AI provider is not configured. Add its API key and model in server settings.')
    # Streaming never reroutes: tokens may already have reached the caller.
    return candidates[0]


def _http_client():
    # Fixed provider destinations, normal TLS verification and deployment proxies.
    return httpx.AsyncClient(timeout=httpx.Timeout(20.0), follow_redirects=False, trust_env=True)


def _request(config, provider, prompt, output_limit):
    model, key = _model(config, provider), _key(config, provider)
    if provider == 'anthropic':
        return ('https://api.anthropic.com/v1/messages',
                {'x-api-key':key, 'anthropic-version':'2023-06-01'},
                {'model':model, 'max_tokens':output_limit, 'stream':True, 'system':INSTRUCTIONS,
                 'messages':[{'role':'user','content':prompt}]})
    if provider == 'openai':
        return ('https://api.openai.com/v1/responses', {'Authorization':'Bearer '+key},
                {'model':model, 'stream':True, 'store':False, 'max_output_tokens':output_limit,
                 'instructions':INSTRUCTIONS, 'input':[{'role':'user','content':prompt}]})
    if provider == 'gemini':
        url = 'https://generativelanguage.googleapis.com/v1beta/models/' + quote(model.removeprefix('models/'), safe='') + ':streamGenerateContent?alt=sse'
        return (url, {'x-goog-api-key':key},
                {'systemInstruction':{'parts':[{'text':INSTRUCTIONS}]},
                 'contents':[{'role':'user','parts':[{'text':prompt}]}],
                 'generationConfig':{'maxOutputTokens':output_limit}})
    return (config.compatible_base_url.rstrip('/')+'/chat/completions', {'Authorization':'Bearer '+key},
            {'model':model, 'max_tokens':output_limit, 'stream':True,
             'messages':[{'role':'system','content':INSTRUCTIONS},{'role':'user','content':prompt}]})


async def _frames(response):
    """Parse data fields incrementally without unbounded line buffering."""
    buffer = b''
    data = []
    frame_bytes = total = count = 0
    started = time.monotonic()
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > MAX_WIRE_BYTES or time.monotonic()-started > 120:
            raise AssistantUnavailable('Provider stream exceeded its response or time limit.')
        buffer += chunk
        while b'\n' in buffer:
            line, buffer = buffer.split(b'\n', 1)
            line = line.removesuffix(b'\r')
            frame_bytes += len(line)+1
            if frame_bytes > MAX_FRAME_BYTES:
                raise AssistantUnavailable('Provider stream exceeded its event limit.')
            if not line:
                if data:
                    count += 1
                    if count > 8192:
                        raise AssistantUnavailable('Provider stream exceeded its event limit.')
                    yield b'\n'.join(data).decode('utf-8')
                data, frame_bytes = [], 0
            elif line.startswith(b'data:'):
                data.append(line[5:].removeprefix(b' '))
        if len(buffer)+frame_bytes > MAX_FRAME_BYTES:
            raise AssistantUnavailable('Provider stream exceeded its event limit.')
    # Unfinished SSE frames never establish completion.
    if buffer or data:
        raise AssistantUnavailable('Provider stream ended with an incomplete event.')


def _declined():
    raise AssistantUnavailable('Provider declined this request; no other provider was contacted.')


def _incomplete():
    raise AssistantUnavailable('Provider stream did not confirm a complete reply. Retry the request.')


def _token_budget_exceeded():
    raise AssistantUnavailable('Provider did not produce a complete reply before its output token limit. Increase the project response budget or ask a narrower question. No partial reply was saved.')


async def stream_assist(config, message, context, provider):
    """Bound the whole request, including connection and stalled token reads."""
    upstream = _native_stream_assist(config,message,context,provider)
    deadline = time.monotonic()+STREAM_TIMEOUT_SECONDS
    try:
        while True:
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            try:
                item = await asyncio.wait_for(anext(upstream),remaining)
            except StopAsyncIteration:
                return
            yield item
    except TimeoutError:
        raise AssistantUnavailable('Provider stream exceeded its time limit. No partial reply was saved.') from None
    finally:
        with anyio.CancelScope(shield=True):
            await upstream.aclose()


async def _native_stream_assist(config, message, context, provider):
    """Yield native text deltas, then one final result only on confirmed completion."""
    prompt, limits = build_prompt(config, message, context)
    output_limit = limits['max_output_tokens']
    max_reply_chars = reply_char_limit({'profile_limits':limits})
    url, headers, body = _request(config, provider, prompt, output_limit)
    model = _model(config, provider)
    reply = []
    length = 0
    complete = stopped = False
    try:
        async with _http_client() as client:
            async with client.stream('POST',url,headers=headers,json=body) as response:
                if not 200 <= response.status_code < 300:
                    raise AssistantUnavailable('Provider '+str(_status_failure(response.status_code))+'. No other provider was contacted.')
                async for raw in _frames(response):
                    delta = ''
                    if raw == '[DONE]':
                        if provider != 'compatible' or not stopped:
                            _incomplete()
                        complete = True
                        break
                    value = json.loads(raw)
                    if not isinstance(value,dict):
                        _incomplete()
                    if value.get('type') == 'response.incomplete' and value.get('response', {}).get('incomplete_details', {}).get('reason') == 'max_output_tokens':
                        _token_budget_exceeded()
                    if value.get('error') or value.get('type') in {'error','response.failed','response.incomplete'}:
                        _incomplete()
                    if provider == 'anthropic':
                        kind = value.get('type')
                        if kind == 'message_start':
                            model = value.get('message',{}).get('model') or model
                        elif kind == 'content_block_delta':
                            part = value.get('delta',{})
                            if part.get('type') == 'text_delta':
                                delta = part.get('text','')
                        elif kind == 'message_delta':
                            reason = value.get('delta',{}).get('stop_reason')
                            if reason == 'refusal':
                                _declined()
                            if reason == 'max_tokens':
                                _token_budget_exceeded()
                            if reason not in {'end_turn','stop_sequence'}:
                                _incomplete()
                            stopped = True
                        elif kind == 'message_stop':
                            if not stopped:
                                _incomplete()
                            complete = True
                    elif provider == 'openai':
                        kind = value.get('type','')
                        if kind.startswith('response.refusal'):
                            _declined()
                        if kind == 'response.output_text.delta':
                            delta = value.get('delta','')
                        if kind in {'response.created','response.completed'}:
                            result = value.get('response',{})
                            model = result.get('model') or model
                            if any(part.get('type')=='refusal' for item in result.get('output',[]) for part in item.get('content',[])):
                                _declined()
                            if kind == 'response.completed':
                                if result.get('status') != 'completed':
                                    _incomplete()
                                complete = True
                    elif provider == 'gemini':
                        model = value.get('modelVersion') or model
                        candidate = (value.get('candidates') or [{}])[0]
                        reason = candidate.get('finishReason')
                        if value.get('promptFeedback',{}).get('blockReason') or reason in {'SAFETY','RECITATION','BLOCKLIST','PROHIBITED_CONTENT','SPII','IMAGE_SAFETY'}:
                            _declined()
                        if reason and reason != 'STOP':
                            if reason == 'MAX_TOKENS':
                                _token_budget_exceeded()
                            _incomplete()
                        delta = ''.join(part['text'] for part in candidate.get('content',{}).get('parts',[]) if not part.get('thought') and isinstance(part.get('text'),str))
                        complete = reason == 'STOP'
                    else:
                        model = value.get('model') or model
                        choice = (value.get('choices') or [{}])[0]
                        part = choice.get('delta',{})
                        reason = choice.get('finish_reason')
                        if part.get('refusal') or reason == 'content_filter':
                            _declined()
                        if reason and reason != 'stop':
                            if reason == 'length':
                                _token_budget_exceeded()
                            _incomplete()
                        stopped = stopped or reason == 'stop'
                        delta = part.get('content') or ''
                    if not isinstance(delta,str) or not isinstance(model,str) or len(model)>200:
                        _incomplete()
                    if delta:
                        length += len(delta)
                        if length > max_reply_chars:
                            raise AssistantUnavailable('Provider reply exceeded the output limit. No partial reply was saved.')
                        reply.append(delta)
                        yield {'event':'delta','text':delta}
                    if complete:
                        break
        text = ''.join(reply).strip()
        if not complete or not text:
            _incomplete()
        validate_reply_sources(text, select_context({**context,'profile_limits':limits}, limits['context_chars']))
        yield {'event':'done','result':{'reply':text,'provider':PROVIDERS[provider],'provider_id':provider,
               'model':model,'fallback_used':False,'attempted_providers':[provider]}}
    except AssistantUnavailable:
        raise
    except (httpx.TimeoutException,httpx.NetworkError):
        raise AssistantUnavailable('Provider connection or timeout failure. No partial reply was saved.') from None
    except Exception:
        # Never echo provider payloads, prompts, SDK errors or configuration secrets.
        raise AssistantUnavailable('Invalid provider stream or configuration. No partial reply was saved.') from None


def sse(event, data):
    return 'event: '+event+'\ndata: '+json.dumps(data,ensure_ascii=False)+'\n\n'


class ReplyStreamingResponse(StreamingResponse):
    """Always monitor disconnects and close the iterator, including unstarted bodies."""
    def __init__(self, content, cleanup):
        super().__init__(content, media_type='text/event-stream', headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})
        self.cleanup = cleanup

    async def __call__(self, scope, receive, send):
        try:
            # ASGI 2.4 only notices disconnects on send. Monitoring receive also
            # cancels stalled upstream reads promptly between outgoing tokens.
            monitored = {**scope, 'asgi':{**scope.get('asgi',{}),'spec_version':'2.3'}}
            await super().__call__(monitored, receive, send)
        finally:
            with anyio.CancelScope(shield=True):
                try:
                    await self.body_iterator.aclose()
                finally:
                    self.cleanup()
