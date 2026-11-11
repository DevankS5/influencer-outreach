"""Restore the authentic delivered observation snapshot without network calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from outreach import db
from outreach.personalization import generate
from outreach.config import campaign_id, ROOT

db.init()
path=ROOT/'data/export/profiles.json'
for p in json.loads(path.read_text(encoding='utf-8')):
    db.save_profile(p)
    try: generate(p,campaign_id())
    except ValueError as e: print(f'Generation skipped {p["id"]}: {e}')
print('Restored observed public profiles; generated unapproved offline drafts. No sending or approval performed.')
