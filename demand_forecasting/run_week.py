"""Run this cumulative week's CLI workflow from any working directory."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
week = json.loads((ROOT/'STAGE.json').read_text())['week']
commands = [['prepare']]
if week >= 2:
    commands += [['baseline']]
if week >= 3:
    commands += [['train'], ['forecast'], ['inventory', '--store', '1', '--item', '1', '--lead-days', '3', '--on-hand', '20', '--daily-std', '5']]
if week >= 4:
    commands += [['sql']]
for command in commands:
    subprocess.run([sys.executable, '-m', 'src.cli', *command], cwd=ROOT, check=True)
print(f'Week {week} command-line workflow completed. Read README.md for the dashboard command.')
