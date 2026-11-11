import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from .config import ROOT
from .db import profiles, messages, connect
from .sending import approve, send


def serve(campaign):
    host=os.getenv('HOST','127.0.0.1'); token=os.getenv('DASHBOARD_TOKEN','')
    if host not in ('127.0.0.1','localhost','::1') and len(token)<24:
        raise ValueError('A DASHBOARD_TOKEN of at least 24 characters is required for non-loopback binding')
    class Handler(BaseHTTPRequestHandler):
        def reply(self, data, status=200, content_type='application/json'):
            raw=data if isinstance(data,bytes) else json.dumps(data).encode()
            self.send_response(status); self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(raw))); self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer'); self.end_headers(); self.wfile.write(raw)
        def allowed(self):
            return not token or secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+token)
        def do_GET(self):
            if urlparse(self.path).path=='/':
                return self.reply((ROOT/'web/index.html').read_bytes(),content_type='text/html; charset=utf-8')
            if urlparse(self.path).path=='/health': return self.reply({'ok':True})
            if not self.allowed(): return self.reply({'error':'Enter dashboard token'},401)
            if urlparse(self.path).path=='/api/data':
                with connect() as c: ds=[dict(r) for r in c.execute('SELECT * FROM deliveries WHERE campaign_id=?',(campaign,))]
                return self.reply({'profiles':profiles(),'messages':messages(campaign),'deliveries':ds,'campaign':campaign})
            return self.reply({'error':'Not found'},404)
        def do_POST(self):
            if not self.allowed(): return self.reply({'error':'Unauthorized'},401)
            # No CORS; reject cross-origin browser mutations, including on loopback.
            origin=self.headers.get('Origin')
            if origin and urlparse(origin).netloc!=self.headers.get('Host'): return self.reply({'error':'Cross-origin request rejected'},403)
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=4096: raise ValueError('Invalid request length')
                data=json.loads(self.rfile.read(length))
                if self.path=='/api/review': approve(data['id'],campaign,bool(data.get('approved',True))); return self.reply({'ok':True})
                if self.path=='/api/simulate': return self.reply({'results':send(campaign,profile_id=data.get('id'))})
                return self.reply({'error':'Not found'},404)
            except (ValueError,KeyError,TypeError) as e: return self.reply({'error':str(e)},400)
        def log_message(self, fmt,*args): pass
    print(f'Dashboard running on {host}:{os.getenv("PORT","8000")}',flush=True)
    ThreadingHTTPServer((host,int(os.getenv('PORT','8000'))),Handler).serve_forever()
