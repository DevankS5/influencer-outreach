"""Only extract literal public email addresses. Never infer demographics."""
import ipaddress
import re
import socket
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin
import requests

EMAIL = re.compile(r'(?<![\w.+-])([A-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?(?:\.[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?)+)', re.I)
BAD_DOMAINS = {'example.com','example.org','example.net','test.com','email.com','domain.com'}

def valid_email(value):
    if not value or len(value) > 254 or '\n' in value or '\r' in value: return False
    m = EMAIL.fullmatch(value)
    return bool(m and value.rsplit('@', 1)[1].lower() not in BAD_DOMAINS and len(value.split('@')[0]) <= 64)

def extract_emails(text):
    return list(dict.fromkeys(e for e in EMAIL.findall(unescape(text or '')) if valid_email(e)))

class Page(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]; self.text=[]; self.hidden=0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'): self.hidden += 1
        for k,v in attrs:
            if tag == 'a' and k == 'href' and v: self.links.append(v)
    def handle_endtag(self, tag):
        if tag in ('script','style'): self.hidden=max(0,self.hidden-1)
    def handle_data(self, data):
        if not self.hidden: self.text.append(data)


def safe_url(url):
    """Best-effort SSRF protection; production must also restrict egress against DNS rebinding."""
    p = urlparse(url)
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password: raise ValueError('Unsafe website URL')
    if p.port not in (None,80,443): raise ValueError('Nonstandard website port')
    for item in socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme=='https' else 80), type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global: raise ValueError('Non-public website address')
    return url

def website_emails(url):
    """Opt-in, robots-aware, max two pages per profile, no redirects or anti-bot bypass."""
    from urllib.robotparser import RobotFileParser
    origin = '{0.scheme}://{0.netloc}'.format(urlparse(safe_url(url)))
    agent = 'EvidenceOutreachPrototype'
    # Conservative: robots must be obtainable and permit collection.
    r = requests.get(origin + '/robots.txt', timeout=10, allow_redirects=False)
    if r.status_code != 200: return []
    robots = RobotFileParser(); robots.parse(r.text.splitlines())
    found=[]; queue=[url]; seen=set()
    for _ in range(2):
        if not queue: break
        target=queue.pop(0)
        if target in seen or not robots.can_fetch(agent,target): continue
        safe_url(target); seen.add(target)
        with requests.get(target, timeout=12, allow_redirects=False, stream=True, headers={'User-Agent':agent}) as response:
            if response.status_code != 200 or 'text/html' not in response.headers.get('Content-Type',''): continue
            chunks=[]; size=0
            for chunk in response.iter_content(16384):
                size += len(chunk)
                if size > 500_000: break
                chunks.append(chunk)
            page=Page(); page.feed(b''.join(chunks).decode('utf-8',errors='replace'))
        for email in extract_emails(' '.join(page.text) + ' ' + ' '.join(x[7:].split('?')[0] for x in page.links if x.startswith('mailto:'))):
            found.append((email,target))
        for link in page.links:
            absolute=urljoin(target,link)
            if urlparse(absolute).netloc==urlparse(url).netloc and any(t in link.lower() for t in ('contact','about')): queue.append(absolute)
        if found: break
    return found


def enrich(p, crawl_web=False):
    evidence=[(p.get('bio',''),p['profile_url'])] + [(x.get('text',''),x['url']) for x in p.get('recent_posts',[])]
    candidates=[]
    for text,source in evidence:
        for address in extract_emails(text): candidates.append({'email':address,'source':source})
    # Bio-only links, never follow links from arbitrary posts.
    links=re.findall(r'https?://[^\s<>]+', p.get('bio',''))
    social={'youtube.com','www.youtube.com','youtu.be','bsky.app','twitter.com','x.com','instagram.com','www.instagram.com','t.co'}
    p['website']=next((u.rstrip('.,)') for u in links if urlparse(u).hostname not in social),None)
    if not candidates and crawl_web and p['website']:
        try:
            candidates.extend({'email':e,'source':s} for e,s in website_emails(p['website']))
        except (requests.RequestException, ValueError, OSError):
            p.setdefault('data_warnings',[]).append('Website enrichment unavailable or disallowed')
    p['email_candidates']=list({x['email']:x for x in candidates}.values())
    p['email']=candidates[0]['email'] if candidates else 'Not Found'
    p['email_source']=candidates[0]['source'] if candidates else None
    p['contact_verified']=False  # Public appearance is not proof of mailbox ownership or deliverability.
    return p
