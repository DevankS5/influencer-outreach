import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from .config import db_path

def now(): return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    path = db_path(); path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback(); raise
    finally: con.close()

def init():
    with connect() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS profiles (
          id TEXT PRIMARY KEY, platform TEXT NOT NULL, name TEXT NOT NULL,
          data TEXT NOT NULL, updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS messages (
          profile_id TEXT NOT NULL REFERENCES profiles(id), campaign_id TEXT NOT NULL,
          subject TEXT NOT NULL, email_body TEXT NOT NULL, dm TEXT NOT NULL,
          generator TEXT NOT NULL, approved INTEGER NOT NULL DEFAULT 0,
          created_at TEXT NOT NULL, PRIMARY KEY(profile_id,campaign_id));
        CREATE TABLE IF NOT EXISTS deliveries (
          id INTEGER PRIMARY KEY, profile_id TEXT NOT NULL, campaign_id TEXT NOT NULL,
          email TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL,
          message_id TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL, UNIQUE(profile_id,campaign_id,mode),
          UNIQUE(email,campaign_id,mode));
        CREATE TABLE IF NOT EXISTS suppressions (
          email TEXT PRIMARY KEY, reason TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS events (
          id INTEGER PRIMARY KEY, event TEXT NOT NULL, detail TEXT NOT NULL, created_at TEXT NOT NULL);
        ''')

def event(kind, detail):
    with connect() as c: c.execute('INSERT INTO events(event,detail,created_at) VALUES(?,?,?)', (kind, str(detail), now()))

def save_profile(p):
    with connect() as c:
        previous = c.execute('SELECT data FROM profiles WHERE id=?', (p['id'],)).fetchone()
        # A changed observation invalidates review; do not silently send stale messages.
        if previous and previous['data'] != json.dumps(p, sort_keys=True):
            c.execute('UPDATE messages SET approved=0 WHERE profile_id=?', (p['id'],))
        c.execute('INSERT INTO profiles VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET platform=excluded.platform,name=excluded.name,data=excluded.data,updated_at=excluded.updated_at',
                  (p['id'], p['platform'], p['name'], json.dumps(p, sort_keys=True), now()))

def profiles():
    with connect() as c: return [json.loads(r['data']) for r in c.execute('SELECT data FROM profiles ORDER BY name')]

def messages(campaign):
    with connect() as c: return [dict(r) for r in c.execute('SELECT * FROM messages WHERE campaign_id=?', (campaign,))]
