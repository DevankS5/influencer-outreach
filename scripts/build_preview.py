"""Build an offline, read-only UI preview from the existing database. No API calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from outreach import db
from outreach.config import ROOT, campaign_id

def main():
    db.init()
    campaign = campaign_id()
    with db.connect() as connection:
        deliveries = [dict(row) for row in connection.execute(
            'SELECT * FROM deliveries WHERE campaign_id=?', (campaign,))]
    snapshot = {'profiles': db.profiles(), 'messages': db.messages(campaign),
                'deliveries': deliveries, 'campaign': campaign}
    payload = json.dumps(snapshot, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
    html = html.replace('<script>', '<script>window.SIGNAL_SNAPSHOT=' + payload + ';</script><script>', 1)
    (ROOT / 'dashboard-preview.html').write_text(html, encoding='utf-8')
    print('Built dashboard-preview.html: embedded observations, no network, read-only actions.')

if __name__ == '__main__':
    main()
