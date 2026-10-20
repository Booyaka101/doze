"""Loopback-only UI. State-changing requests require a per-process CSRF token."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlsplit

from . import compiler
from .demo import PROMPT, RECIPE, CASES, seed
from .engine import Engine, SafetyError, validate_cases
from .replay import replay
from . import close, close_demo, close_inference

STATIC = Path(__file__).parent / 'static'


def make_server(engine, port=8741, demo=True):
    token = secrets.token_urlsafe(32)
    inference_enabled = threading.Event()
    inference_enabled.set()
    inference_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, payload, mime='application/json; charset=utf-8'):
            content = json.dumps(payload).encode() if isinstance(payload, (dict, list)) else payload
            self.send_response(status)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(content)

        def trusted_host(self):
            return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}

        def do_GET(self):
            if not self.trusted_host():
                return self.reply(403, {'error': 'Loopback host required.'})
            route = urlsplit(self.path).path
            try:
                if route == '/api/state':
                    return self.reply(200, {'token': token, 'workspace': str(engine.root), 'demo': demo,
                                            'inference_enabled': inference_enabled.is_set(),
                                            'files': engine.inventory(), 'recipes': engine.recipes(),
                                            'runs': engine.runs(), 'sample_prompt': PROMPT, 'sample_cases': CASES})
                if route == '/api/models':
                    return self.reply(200, {'models': compiler.models() if inference_enabled.is_set() else []})
                if route in {'/', '/files', '/app.js', '/style.css', '/lab.css', '/teaching.css', '/mark.svg', '/close.js', '/close.css'}:
                    name = 'close.html' if route == '/' else 'index.html' if route == '/files' else route[1:]
                    mime = {'html': 'text/html', 'js': 'text/javascript', 'css': 'text/css', 'svg': 'image/svg+xml'}[name.split('.')[-1]]
                    return self.reply(200, (STATIC / name).read_bytes(), mime + '; charset=utf-8')
                return self.reply(404, {'error': 'Not found.'})
            except SafetyError as error:
                return self.reply(400, {'error': str(error)})

        def do_POST(self):
            if not self.trusted_host() or not secrets.compare_digest(self.headers.get('X-Doze-Token', ''), token):
                return self.reply(403, {'error': 'Refresh the local app before making changes.'})
            origin = self.headers.get('Origin')
            if origin and origin not in {f'http://127.0.0.1:{self.server.server_port}', f'http://localhost:{self.server.server_port}'}:
                return self.reply(403, {'error': 'Cross-origin requests are not allowed.'})
            try:
                route = urlsplit(self.path).path
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= (1000000 if route.startswith('/api/close/') else 64000):
                    raise SafetyError('Invalid request size.')
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    raise SafetyError('JSON required.')
                body = json.loads(self.rfile.read(length))
                route = urlsplit(self.path).path
                if not isinstance(body, dict):
                    raise SafetyError('Expected an object.')
                if route == '/api/close/demo':
                    return self.reply(200, close_demo.demo(body.get('scenario', 'messy'), body.get('week', 1)))
                if route == '/api/close/inspect':
                    result = {}
                    for side in ('payments', 'bank'):
                        headers, rows = close.table(body[side + '_csv'])
                        result[side] = {'headers': headers, 'records': len(rows), 'rows': rows}
                    return self.reply(200, result)
                if route == '/api/close/sample-profile':
                    return self.reply(200, {'profile': close.profile(close_demo.MAPPING, close_demo.PAYMENT_HEADERS, close_demo.BANK_HEADERS),
                                            'provenance': {'source': 'hand-written sample, not AI output', 'model_calls': 0}})
                if route == '/api/close/profile':
                    return self.reply(200, close.validate_profile(body['profile']))
                if route == '/api/close/teach':
                    if body.get('headers_approved') is not True:
                        raise SafetyError('Explicit approval to send these column names to local Ollama is required.')
                    if not inference_lock.acquire(blocking=False):
                        raise SafetyError('A compilation is already running. No duplicate job started.')
                    try:
                        if not inference_enabled.is_set():
                            raise SafetyError('AI is asleep. Inference is blocked by the server. Existing profiles still work.')
                        result = close_inference.compile_mapping(body.get('payment_headers'), body.get('bank_headers'),
                            body.get('model'), body.get('decimal_mark', '.'), body.get('hint', ''))
                    finally:
                        inference_lock.release()
                    return self.reply(200, result)
                if route == '/api/close/reconcile':
                    if body.get('mapping_approved') is not True:
                        raise SafetyError('Review and approve the exact column mapping first.')
                    return self.reply(200, close.reconcile(body['profile'], body['payments_csv'], body['bank_csv']))
                if route == '/api/close/packet':
                    if body.get('mapping_approved') is not True or body.get('report_approved') is not True:
                        raise SafetyError('Explicit mapping and report review are required before a handoff.')
                    return self.reply(200, close.packet(body['profile'], body['payments_csv'], body['bank_csv'], body['approved_sha256']), 'application/zip')
                if route == '/api/compile':
                    # Reject missing/invalid teaching input before starting any inference.
                    examples = validate_cases(body.get('examples'))
                    if not inference_lock.acquire(blocking=False):
                        raise SafetyError('A local compilation is already running. No duplicate job was started.')
                    try:
                        if not inference_enabled.is_set():
                            raise SafetyError('AI is asleep. Inference is blocked by the server. Existing recipes still run.')
                        previous = engine.recipe(body['previous_id']) if body.get('previous_id') else None
                        result = compiler.compile_chore(body.get('prompt'), body.get('model'), examples, previous)
                    finally:
                        inference_lock.release()
                    saved = engine.save_recipe(result['recipe'], examples)
                    return self.reply(200, {**saved, 'provenance': result['provenance']})
                if route == '/api/inference':
                    if type(body.get('enabled')) is not bool:
                        raise SafetyError('Choose whether local inference is enabled.')
                    if not inference_lock.acquire(blocking=False):
                        raise SafetyError('Wait for the active compilation before changing inference mode.')
                    try:
                        inference_enabled.set() if body['enabled'] else inference_enabled.clear()
                    finally:
                        inference_lock.release()
                    return self.reply(200, {'inference_enabled': inference_enabled.is_set()})
                if route == '/api/recipe':
                    return self.reply(200, engine.save_recipe(body['recipe'], body.get('examples')))
                if route == '/api/certify':
                    return self.reply(200, engine.save_recipe(engine.recipe(body['recipe_id']), body['cases']))
                if route == '/api/preview':
                    return self.reply(200, engine.preview(body['recipe_id']))
                if route == '/api/probe':
                    return self.reply(200, engine.probe(body['recipe_id'], body['cases']))
                if route == '/api/replay':
                    return self.reply(200, replay(engine.recipe(body['recipe_id']), engine.database.parent))
                if route == '/api/execute':
                    if body.get('approved') is not True:
                        raise SafetyError('Explicit approval of the preview is required.')
                    return self.reply(200, engine.execute(body['plan_id']))
                if route == '/api/undo':
                    return self.reply(200, engine.undo(body['run_id']))
                if route == '/api/demo':
                    if not demo:
                        raise SafetyError('Sample creation is disabled for custom workspaces.')
                    return self.reply(200, {'added': seed(engine, body.get('batch', 'first'))})
                if route == '/api/sample-recipe':
                    return self.reply(200, engine.save_recipe(RECIPE, CASES))
                if route == '/api/mistake':
                    # This is the actual structure from our first recorded Gemma response.
                    mistake = json.loads(json.dumps(RECIPE))
                    mistake['name'] = 'Recorded Gemma mistake: too broad'
                    mistake['rules'][0]['when'] = {'name_starts_with': 'screenshot', 'max_bytes': 2147483648}
                    return self.reply(200, engine.save_recipe(mistake, CASES))
                return self.reply(404, {'error': 'Not found.'})
            except (SafetyError, KeyError, ValueError, TypeError) as error:
                return self.reply(400, {'error': str(error)})
            except OSError:
                return self.reply(409, {'error': 'Filesystem conflict. Rehearse again or review the latest receipt.'})

    return ThreadingHTTPServer(('127.0.0.1', port), Handler)


def main():
    parser = argparse.ArgumentParser(description='Doze: teach a chore once. Let the model sleep.')
    parser.add_argument('--port', type=int, default=8741)
    parser.add_argument('--workspace', type=Path, help='Explicitly opt in to a real folder; sample creation is disabled.')
    parser.add_argument('--state', type=Path, default=Path('.doze'))
    args = parser.parse_args()
    engine = Engine(args.workspace or args.state / 'sample-workspace', args.state)
    if args.workspace is None and not engine.inventory():
        seed(engine)
    server = make_server(engine, args.port, demo=args.workspace is None)
    print(f'Doze at http://127.0.0.1:{server.server_port} | workspace: {engine.root}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
