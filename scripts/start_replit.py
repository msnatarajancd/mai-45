"""Run the existing application as one web process on Replit or locally.

Use Python 3.12 in the Replit project. This starts no public hosting operation;
Replit Publishing access and billing are configured in the platform separately.
"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw_port = os.environ.get('PORT', '8501')
    try:
        port = int(raw_port)
    except ValueError:
        raise SystemExit('PORT must be an integer between 1 and 65535.') from None
    if not 1 <= port <= 65535:
        raise SystemExit('PORT must be an integer between 1 and 65535.')
    os.chdir(ROOT)
    # These files are demo-only. No durability across publishing/restarts implied.
    os.environ.setdefault('READYRELIEF_DB_PATH', str(ROOT / '.local' / 'recovery.sqlite3'))
    os.environ.setdefault('READYRELIEF_PROGRESS_DB_PATH', str(ROOT / '.local' / 'recovery-progress.sqlite3'))
    os.environ.setdefault('LANGSMITH_TRACING', 'false')
    os.environ.setdefault('LANGCHAIN_TRACING_V2', 'false')
    host = os.environ.get('READYRELIEF_BIND_ADDRESS', '0.0.0.0')
    os.execv(sys.executable, [sys.executable, '-m', 'streamlit', 'run', str(ROOT / 'app.py'),
        '--server.address=' + host, '--server.port=' + str(port),
        '--server.headless=true', '--browser.gatherUsageStats=false'])


if __name__ == '__main__':
    main()
