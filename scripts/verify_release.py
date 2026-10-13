"""Verify the file checksums included in an extracted release (integrity, not authenticity)."""
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=ROOT/'SHA256SUMS.txt'
if not manifest.is_file():raise SystemExit('SHA256SUMS.txt is created by package_release.py in the ZIP release.')
failures=[];count=0
for line in manifest.read_text().splitlines():
 digest,name=line.split('  ',1)
 path=(ROOT/name).resolve()
 if ROOT not in path.parents or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest: failures.append(name)
 count+=1
if failures: raise SystemExit('Changed or missing files: '+', '.join(failures))
print(f'All {count} packaged source and asset files match their release checksums.')
