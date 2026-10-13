"""Serve the full app from one process. Keep this terminal open."""
from pathlib import Path
import os
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Set these before importing NumPy/scikit-learn through the application.
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ.setdefault(variable, '1')

def main():
    if sys.version_info[:2] != (3, 12):
        sys.exit('Use Python 3.12. Run SETUP_WINDOWS.bat or python3.12 scripts/setup.py first.')
    try:
        import uvicorn
        from backend.app.config import settings
    except ImportError:
        sys.exit('Dependencies missing. Run SETUP_WINDOWS.bat or python3.12 scripts/setup.py first.')
    if not (settings.path(settings.frontend_dist) / 'index.html').exists():
        sys.exit('UI build missing. Run npm ci and npm run build in frontend/.')
    if settings.auth_mode == 'session' and len(settings.setup_token) < 24:
        print('First-owner setup needs SETUP_TOKEN (at least 24 characters) in .env. Run setup again to generate a missing token.', flush=True)
    print(f'Open http://{settings.api_host}:{settings.api_port} in your browser. Press Ctrl+C to stop.', flush=True)
    uvicorn.run('backend.app.main:app', host=settings.api_host, port=settings.api_port, workers=1, proxy_headers=False)

if __name__ == '__main__':
    main()
