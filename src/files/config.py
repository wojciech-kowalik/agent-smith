import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OUTPUT_DIR = os.path.join(os.path.expanduser('~'), '.smith', 'output')


def resolve_output_dir(env=os.environ) -> str:
    """Where exported PDFs go: SMITH_OUTPUT_DIR from .env (``~`` allowed), else ~/.smith/output."""
    configured = env.get('SMITH_OUTPUT_DIR', '').strip()
    return os.path.abspath(os.path.expanduser(configured)) if configured else DEFAULT_OUTPUT_DIR


# Application configuration
LOG_DIR = os.path.join(os.path.expanduser('~'), '.smith')
OUTPUT_DIR = resolve_output_dir()
WAL_FILE = os.path.join(LOG_DIR, 'smith-wal.json')

os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
