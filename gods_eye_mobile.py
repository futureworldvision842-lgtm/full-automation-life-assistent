"""Paired, read-only LAN viewer for the keyless original MIT God's Eye View.

Serves only the built public assets. The local development server and its
credential settings, paid APIs, source files and HMR are never LAN-exposed.
"""
from contextlib import asynccontextmanager
import hmac
import html
import io
import ipaddress
import json
from pathlib import Path
import re
import secrets
import socket
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
import uvicorn

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'integrations/gods-eye-view/dist'
TOKEN_FILE = ROOT / 'config/globe-mobile.local.json'
UPSTREAM = 'http://127.0.0.1:4173'
COOKIE = 'jarvis_globe'
PORT = 8766


def load_token():
    try:
        token = json.loads(TOKEN_FILE.read_text(encoding='utf-8')).get('access_token', '')
        if isinstance(token, str) and len(token) >= 43:
            return token
    except (OSError, ValueError, AttributeError):
        pass
    token = secrets.token_urlsafe(32)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps({'access_token': token}), encoding='utf-8')
    return token


TOKEN = load_token()


def authorized(token):
    return isinstance(token, str) and hmac.compare_digest(token.encode(), TOKEN.encode())


def valid_host(host):
    if host in {'localhost:8766', '127.0.0.1:8766', '[::1]:8766'}:
        return True
    try:
        address, port = host.rsplit(':', 1)
        ip = ipaddress.IPv4Address(address)
        return port == str(PORT) and any(ip in ipaddress.ip_network(net) for net in ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16'))
    except (ValueError, AttributeError):
        return False


def read_only_api(method, path):
    if method == 'POST':
        return path == '/api/overpass'
    if method != 'GET':
        return False
    if path in {'/api/terrain/heights', '/api/route', '/api/adsblol/mil', '/api/adsblol/trace',
                '/api/military-installations', '/api/regional-brief', '/api/weather-effects',
                '/api/radio/stations', '/api/tomtom/status', '/api/launches', '/api/opensky'}:
        return True
    return bool(re.fullmatch(r'/api/(?:celestrak/(?:stations|visual|gps-ops|glo-ops|galileo|geo|starlink|active)|adsbdb/type/[a-fA-F0-9]{6}|adsbdb/route/[A-Z0-9]{2,8})', path))


@asynccontextmanager
async def lifespan(app):
    async with httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False,
                                 limits=httpx.Limits(max_connections=8)) as client:
        app.state.client = client
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware('http')
async def ingress(request, call_next):
    if not valid_host(request.headers.get('host', '')):
        return JSONResponse({'error': 'invalid_host'}, status_code=403)
    origin = request.headers.get('origin')
    if (origin and origin.rstrip('/') != str(request.base_url).rstrip('/')) or request.headers.get('sec-fetch-site') == 'cross-site':
        return JSONResponse({'error': 'same_origin_required'}, status_code=403)
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' http://127.0.0.1:8770 http://localhost:8770"
    return response


@app.get('/api/health')
async def health():
    ready = (DIST / 'index.html').is_file()
    return JSONResponse({'ok': ready, 'service': 'jarvis-globe-mobile', 'mode': 'paired-read-only-keyless'}, status_code=200 if ready else 503)


@app.get('/api/mobile/qr')
async def pairing(request: Request):
    if not request.client or request.client.host not in {'127.0.0.1', '::1', 'testclient'}:
        return JSONResponse({'error': 'pair_on_owner_pc'}, status_code=403)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(('8.8.8.8', 80))
            address = sock.getsockname()[0]
        except OSError:
            address = '127.0.0.1'
    url = f'http://{address}:{PORT}/?' + urlencode({'token': TOKEN})
    import qrcode
    import qrcode.image.svg
    out = io.BytesIO()
    qrcode.make(url, image_factory=qrcode.image.svg.SvgPathImage).save(out)
    return HTMLResponse('<!doctype html><meta name="viewport" content="width=device-width">'
                        '<h1>Pair Gods Eye View</h1><p>Trusted Wi-Fi only. HTTP is not encrypted. Do not forward this port to the internet.</p>'
                        + out.getvalue().decode() + '<p>Paste this pairing URL into the Android app:</p><textarea readonly rows="4" style="width:95%">'
                        + html.escape(url) + '</textarea>')


@app.api_route('/{path:path}', methods=['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
async def viewer(path: str, request: Request):
    if path == '' and request.method == 'GET' and authorized(request.query_params.get('token', '')):
        response = RedirectResponse('/', status_code=303)
        response.set_cookie(COOKIE, TOKEN, httponly=True, samesite='strict', secure=request.url.scheme == 'https', max_age=86400)
        return response
    supplied = request.cookies.get(COOKIE, '') or request.headers.get('X-Jarvis-Globe-Token', '')
    if not authorized(supplied):
        return JSONResponse({'error': 'globe_pairing_required'}, status_code=401)
    route = '/' + path
    if route.startswith('/api/'):
        if not read_only_api(request.method, route):
            return JSONResponse({'error': 'provider_or_write_route_disabled', 'mode': 'read-only-keyless'}, status_code=403)
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > 24576:
                return JSONResponse({'error': 'body_too_large'}, status_code=413)
        if request.method == 'POST' and request.headers.get('content-type', '').split(';')[0] != 'application/x-www-form-urlencoded':
            return JSONResponse({'error': 'unsupported_content_type'}, status_code=415)
        headers = {'User-Agent': 'Jarvis-ReadOnly-Globe/1.0', 'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            async with request.app.state.client.stream(request.method, UPSTREAM + route,
                    params=list(request.query_params.multi_items()), content=bytes(body), headers=headers) as upstream:
                if upstream.is_redirect:
                    return JSONResponse({'error': 'upstream_redirect_denied'}, status_code=502)
                payload = bytearray()
                async for chunk in upstream.aiter_bytes():
                    payload.extend(chunk)
                    if len(payload) > 16 * 1024 * 1024:
                        return JSONResponse({'error': 'upstream_too_large'}, status_code=502)
                return Response(bytes(payload), status_code=upstream.status_code,
                                media_type=upstream.headers.get('content-type', 'application/json'))
        except httpx.HTTPError:
            return JSONResponse({'error': 'globe_upstream_unavailable'}, status_code=503)
    if request.method not in {'GET', 'HEAD'}:
        return JSONResponse({'error': 'read_only'}, status_code=405)
    target = (DIST / (path or 'index.html')).resolve()
    if not target.is_relative_to(DIST.resolve()) or not target.is_file() or any(part.startswith('.') for part in Path(path).parts):
        return JSONResponse({'error': 'not_found'}, status_code=404)
    return FileResponse(target)


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=PORT, access_log=False)
