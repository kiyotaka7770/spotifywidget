import http.server
import urllib.parse
import urllib.request
import json
import os
import base64

PORT = 8888
DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(DIR, 'tokens.json')
OBS_FILE = os.path.join(DIR, 'obs-overlay.html')

def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_tokens(data):
    with open(TOKEN_FILE, 'w') as f:
        json.dump(data, f)

def generate_obs_file(tokens):
    access_token = tokens.get('access_token', '')
    refresh_token = tokens.get('refresh_token', '')
    client_id = tokens.get('client_id', '')
    client_secret = tokens.get('client_secret', '')
    html = open(os.path.join(DIR, 'spotify-overlay.html'), 'r', encoding='utf-8').read()
    # Inject tokens before </script> closing or at end of init
    inject = f"""
  // Injected by server
  window._SPOTIFY_TOKENS = {{
    access_token: {json.dumps(access_token)},
    refresh_token: {json.dumps(refresh_token)},
    client_id: {json.dumps(client_id)},
    client_secret: {json.dumps(client_secret)}
  }};
"""
    html = html.replace('<script>', '<script>\n' + inject, 1)
    with open(OBS_FILE, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Generated obs-overlay.html with fresh tokens')

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIR, **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if 'code' in qs:
            code = qs['code'][0]
            tokens = load_tokens()
            client_id = tokens.get('client_id', '')
            client_secret = tokens.get('client_secret', '')
            if client_id and client_secret:
                creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
                data = urllib.parse.urlencode({
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': f'http://127.0.0.1:{PORT}'
                }).encode()
                req = urllib.request.Request(
                    'https://accounts.spotify.com/api/token',
                    data=data,
                    headers={
                        'Authorization': f'Basic {creds}',
                        'Content-Type': 'application/x-www-form-urlencoded'
                    }
                )
                try:
                    with urllib.request.urlopen(req) as resp:
                        token_data = json.loads(resp.read())
                        tokens['access_token'] = token_data.get('access_token', '')
                        tokens['refresh_token'] = token_data.get('refresh_token', tokens.get('refresh_token', ''))
                        save_tokens(tokens)
                        generate_obs_file(tokens)
                except Exception as e:
                    print(f'Token exchange error: {e}')
            self.send_response(302)
            self.send_header('Location', '/spotify-overlay.html')
            self.end_headers()
            return

        if parsed.path == '/save-creds':
            client_id = qs.get('client_id', [''])[0]
            client_secret = qs.get('client_secret', [''])[0]
            tokens = load_tokens()
            tokens['client_id'] = client_id
            tokens['client_secret'] = client_secret
            save_tokens(tokens)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        if parsed.path == '/tokens':
            tokens = load_tokens()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(tokens).encode())
            return

        if parsed.path == '/save-token':
            access_token = qs.get('access_token', [''])[0]
            refresh_token = qs.get('refresh_token', [''])[0]
            tokens = load_tokens()
            if access_token:
                tokens['access_token'] = access_token
            if refresh_token:
                tokens['refresh_token'] = refresh_token
            save_tokens(tokens)
            generate_obs_file(tokens)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return

        if parsed.path == '/':
            self.path = '/spotify-overlay.html'

        super().do_GET()

    def log_message(self, format, *args):
        pass

# Generate obs file on startup if tokens exist
tokens = load_tokens()
if tokens.get('access_token'):
    generate_obs_file(tokens)

print(f'Server: http://127.0.0.1:{PORT}')
print(f'OBS file: {OBS_FILE}')
with http.server.HTTPServer(('127.0.0.1', PORT), Handler) as httpd:
    httpd.serve_forever()
