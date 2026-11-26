# -*- coding: utf-8 -*-
"""Локальний перегляд зібраного сайту: python serve.py → http://localhost:8137

Імітує поведінку хостингу: /blog віддає blog.html, старі адреси статей
перенаправляються на нові (301), невідомі адреси отримують 404.html.
"""
import http.server, socketserver, sys
from pathlib import Path
from urllib.parse import urlsplit

DIST = Path(__file__).parent / 'dist'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8137
REDIRECTS = {}
rf = DIST / '_redirects'
if rf.exists():
    for ln in rf.read_text(encoding='utf-8').splitlines():
        p = ln.split()
        if len(p) == 3 and not ln.startswith('#'):
            REDIRECTS[p[0]] = p[1]


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(DIST), **k)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path in REDIRECTS:
            return self._redir(REDIRECTS[path])
        if len(path) > 1 and path.endswith('/'):
            return self._redir(path.rstrip('/'))
        if path.endswith('.html'):
            return self._redir(path[:-5] if path != '/index.html' else '/')
        f = DIST / path.lstrip('/')
        if path == '/' or f.is_file():
            return super().do_GET()
        if (DIST / (path.lstrip('/') + '.html')).is_file():
            self.path = path + '.html'
            return super().do_GET()
        body = (DIST / '404.html').read_bytes()
        self.send_response(404)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redir(self, to):
        self.send_response(301)
        self.send_header('Location', to)
        self.end_headers()


if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(('127.0.0.1', PORT), H) as s:
        print(f'http://localhost:{PORT}')
        s.serve_forever()
