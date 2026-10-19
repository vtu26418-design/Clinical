"""Export bundled saved-model accuracy using the running Docker application's dependencies."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import webbrowser

ROOT=Path(__file__).resolve().parents[1]


def bundled_model(task, model_id=None):
    entries=json.loads((ROOT/'examples/approved-models-v5.json').read_text(encoding='utf-8'))['models']
    entries=[entry for entry in entries if entry.get('task')==task and (not model_id or entry.get('id')==model_id)]
    if not entries:raise ValueError('Choose a bundled model ID for this task from Model Registry.')
    entry=next((entry for entry in entries if entry.get('release_default')),entries[0])
    relative=Path(entry['directory'])
    if relative.is_absolute() or (ROOT/relative).is_symlink() or (ROOT/relative).resolve().parent!=(ROOT/'examples').resolve():
        raise ValueError('Bundled model directory is invalid.')
    return entry


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',choices=['duration','phase'],default='duration')
    parser.add_argument('--no-open',action='store_true')
    parser.add_argument('--model-id',help='Bundled model ID; defaults to the current release research model, not a project activation')
    args=parser.parse_args(argv)
    if not shutil.which('docker'):
        parser.exit(2,'Docker was not found. Install/start Docker Desktop, then run START_DOCKER_WINDOWS.bat.\n')
    name=f'model-accuracy-{args.task}-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination=ROOT/'reports'/name
    container_path='/app/results/'+name
    try:
        selected=bundled_model(args.task,args.model_id)
        subprocess.run(['docker','compose','exec','-T','workbench','python','scripts/generate_model_report.py','--run-dir','/app/'+selected['directory'],'--output-dir',container_path],cwd=ROOT,check=True)
        destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists():raise FileExistsError('A report with this name already exists; no files were overwritten.')
        subprocess.run(['docker','compose','cp','workbench:'+container_path,str(destination)],cwd=ROOT,check=True)
        page=destination/'model_analysis.html'
        if not page.is_file():raise FileNotFoundError('The copied HTML report is missing.')
    except (OSError,ValueError,subprocess.CalledProcessError) as error:
        parser.exit(2,f'Report export failed: {error}\nStart the workbench with START_DOCKER_WINDOWS.bat and retry.\n')
    print('Bundled research model: '+selected['id']+'; project active models are inspected in Settings > Model quality.')
    print('Report saved to: '+str(destination))
    if not args.no_open:webbrowser.open(page.resolve().as_uri())
    return 0


if __name__=='__main__':raise SystemExit(main())
