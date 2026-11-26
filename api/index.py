"""Vercel entrypoint: the same stdlib handler as `outreach.cli serve`, on an ephemeral /tmp SQLite DB."""
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DATABASE_PATH', '/tmp/outreach.sqlite3')

from outreach import db  # noqa: E402
from outreach.config import campaign_id  # noqa: E402
from outreach.server import make_handler  # noqa: E402
from outreach.snapshot import restore  # noqa: E402

# ponytail: /tmp state lives per warm instance; approvals and simulations reset on cold start.
# Move to hosted Postgres if review state must persist across instances.
db.init()
if not db.profiles():
    restore(campaign_id())

# Open read-only demo for reviewers: sending is simulation-only (no SMTP, LIVE_SEND_ENABLED=no) and the data
# is the public snapshot with third-party emails redacted. Set DASHBOARD_TOKEN to lock it down.
class handler(make_handler(campaign_id(), os.getenv('DASHBOARD_TOKEN', ''))):
    # vercel.json rewrites every path to this function and passes the original one as ?__path=
    def _restore_path(self):
        q = parse_qs(urlparse(self.path).query)
        if '__path' in q:
            self.path = q['__path'][0] or '/'

    def do_GET(self):
        self._restore_path(); super().do_GET()

    def do_POST(self):
        self._restore_path(); super().do_POST()
