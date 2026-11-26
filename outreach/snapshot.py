"""Load the delivered public-observation snapshot (and committed LLM drafts) into the local DB."""
import json
from . import db
from .config import ROOT
from .personalization import generate

PROFILES = ROOT / 'data/export/profiles.json'
LLM_MESSAGES = ROOT / 'data/export/messages_llm.json'


def restore(campaign):
    db.init()
    for p in json.loads(PROFILES.read_text(encoding='utf-8')):
        db.save_profile(p)
    drafts = json.loads(LLM_MESSAGES.read_text(encoding='utf-8')) if LLM_MESSAGES.exists() else []
    with db.connect() as c:
        for m in drafts:
            c.execute('''INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?,0,?)''',
                      (m['profile_id'], campaign, m['subject'], m['email_body'], m['dm'], m['generator'], m['created_at']))
    # Anything without a committed LLM draft gets the clearly labeled offline fallback.
    for p in db.profiles():
        try: generate(p, campaign)
        except ValueError: pass


def dump_llm_messages(campaign):
    rows = [m for m in db.messages(campaign) if m['generator'].startswith('llm:')]
    keep = ('profile_id', 'subject', 'email_body', 'dm', 'generator', 'created_at')
    LLM_MESSAGES.write_text(json.dumps([{k: m[k] for k in keep} for m in rows], indent=1, ensure_ascii=False), encoding='utf-8')
    return len(rows)
