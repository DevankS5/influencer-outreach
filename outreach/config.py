import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent

def load_env():
    p = ROOT / '.env'
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
load_env()

def db_path():
    p = Path(os.getenv('DATABASE_PATH', 'data/outreach.sqlite3'))
    return p if p.is_absolute() else ROOT / p

def campaign_id(): return os.getenv('CAMPAIGN_ID', 'tech-ugc-2026')
def brand():
    return {'name': os.getenv('BRAND_NAME', 'Your Brand'),
            'description': os.getenv('BRAND_DESCRIPTION', 'an educational technology product for curious learners'),
            'offer': os.getenv('CAMPAIGN_OFFER', 'a paid educational content collaboration')}
