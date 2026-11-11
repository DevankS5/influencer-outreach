import time
import requests

class APIError(RuntimeError): pass

class Client:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = 'EvidenceOutreachPrototype/1.0 (public profile research; no automated DMs)'
    def get(self, url, params=None):
        for attempt in range(4):
            try:
                r = self.session.get(url, params=params, timeout=(10, 35))
                if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                    time.sleep(min(30, float(r.headers.get('Retry-After', 2 ** attempt))))
                    continue
                r.raise_for_status()
                return r.json()
            except (requests.RequestException, ValueError) as e:
                if attempt == 3: raise APIError(f'GET {url.split("?")[0]} failed ({type(e).__name__})') from None
                time.sleep(2 ** attempt)
        raise APIError('Retries exhausted')
