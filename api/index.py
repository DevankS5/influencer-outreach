"""Vercel entrypoint: the same stdlib handler as `outreach.cli serve`, on an ephemeral /tmp SQLite DB."""
import os
import sys
from pathlib import Path

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

handler = make_handler(campaign_id(), os.getenv('DASHBOARD_TOKEN', ''))
