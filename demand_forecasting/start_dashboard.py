"""Start or restart the Python dashboard using the current virtual environment."""
from pathlib import Path
import subprocess
import sys

if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    subprocess.run([sys.executable, '-m', 'streamlit', 'run', str(root/'app/dashboard.py')], cwd=root, check=True)
