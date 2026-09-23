"""Local-only, text-only chat for the owner-selected reference frontend.

Kept isolated from concurrently edited cockpit integrations. Dashboard ingress
authenticates the caller; this adapter never dispatches tools or cloud calls.
"""
import json
import requests
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

router = APIRouter()


def local_chat(prompt, history):
    with requests.Session() as session:
        session.trust_env = False
        tags = session.get('http://127.0.0.1:11434/api/tags', timeout=4)
        tags.raise_for_status()
        names = [m.get('name') for m in tags.json().get('models', []) if isinstance(m, dict) and isinstance(m.get('name'), str)]
        model = next((n for n in names if n == 'qwen2.5:0.5b'), next(iter(names), None))
        if not model:
            raise ValueError('No local model is installed.')
        messages = [{'role': 'system', 'content': (
            'You are Jarvis. Answer concisely in the language of the user. This is text-only local chat. '
            'You cannot execute tools, inspect screens or place orders. Never claim you did. '
            'Do not invent live market data, balances, completed tasks or guaranteed profits. '
            'Tell the user when current verified data is needed.')}]
        messages.extend(history[-8:])
        messages.append({'role': 'user', 'content': prompt})
        result = session.post('http://127.0.0.1:11434/api/chat', json={
            'model': model, 'messages': messages, 'stream': False,
            'options': {'num_predict': 240, 'temperature': 0.4},
        }, timeout=90)
        result.raise_for_status()
        content = result.json().get('message', {}).get('content', '').strip()
        if not content:
            raise ValueError('The local model returned no text.')
        return {'ok': True, 'text': content, 'provider': 'ollama', 'model': model,
                'executed': False, 'mode': 'local-text-only'}


@router.post('/api/reference-ui/local-chat')
async def reference_local_chat(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 16384:
            return JSONResponse({'ok': False, 'executed': False, 'error': 'Request too large'}, status_code=413)
    try:
        body = json.loads(raw)
        prompt, history = body.get('prompt', ''), body.get('history', [])
        if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 4000 or not isinstance(history, list):
            raise ValueError()
        if len(history) > 12 or any(not isinstance(x, dict) or x.get('role') not in {'user', 'assistant'}
                or not isinstance(x.get('content'), str) or len(x['content']) > 4000 for x in history):
            raise ValueError()
    except (ValueError, TypeError, AttributeError):
        return JSONResponse({'ok': False, 'executed': False, 'error': 'Invalid chat payload'}, status_code=400)
    try:
        return await run_in_threadpool(local_chat, prompt.strip(), history)
    except (requests.RequestException, ValueError, KeyError, TypeError, AttributeError):
        return JSONResponse({'ok': False, 'executed': False,
            'error': 'Local model unavailable or timed out. No cloud provider was called.'}, status_code=503)
