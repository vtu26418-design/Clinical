"""Export bundled saved-model accuracy using the running Docker application's dependencies."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import webbrowser

ROOT=Path(__file__).resolve().parents[1]


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',choices=['duration','phase'],default='duration')
    parser.add_argument('--no-open',action='store_true')
    args=parser.parse_args(argv)
    if not shutil.which('docker'):
        parser.exit(2,'Docker was not found. Install/start Docker Desktop, then run START_DOCKER_WINDOWS.bat.\n')
    name=f'model-accuracy-{args.task}-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination=ROOT/'reports'/name
    container_path='/app/results/'+name
    try:
        subprocess.run(['docker','compose','exec','-T','workbench','python','scripts/generate_model_report.py','--run-dir',f'/app/examples/starter-{args.task}-v5','--output-dir',container_path],cwd=ROOT,check=True)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():raise FileExistsError('A report with this name already exists; no files were overwritten.')
        subprocess.run(['docker','compose','cp','workbench:'+container_path,str(destination)],cwd=ROOT,check=True)
        page=destination/'model_analysis.html'
        if not page.is_file():raise FileNotFoundError('The copied HTML report is missing.')
    except (OSError,subprocess.CalledProcessError) as error:
        parser.exit(2,f'Report export failed: {error}\nStart the workbench with START_DOCKER_WINDOWS.bat and retry.\n')
    print('Report saved to: '+str(destination))
    if not args.no_open:webbrowser.open(page.resolve().as_uri())
    return 0


if __name__=='__main__':raise SystemExit(main())
