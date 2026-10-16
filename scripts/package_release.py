"""Create a source release including prebuilt UI, excluding runtime data and secrets."""
import argparse
import hashlib
import os
import re
from pathlib import Path
import zipfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--version',default='5.2.0.4')
    args=parser.parse_args()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:\.[0-9]+)?",args.version):
        parser.error("Version must use three or four numeric components.")
    release_root="Clinical-Trial-Intelligence-Workbench-v"+args.version
    output=Path(args.output).resolve()
    if ROOT in output.parents:
        parser.error('Write the archive outside the project tree.')
    if not (ROOT/'frontend/dist/index.html').is_file():
        parser.error('Build the frontend first.')
    selected=[]
    for folder, dirs, files in os.walk(ROOT):
        rel=Path(folder).relative_to(ROOT)
        dirs[:]=[d for d in dirs if not d.startswith('.venv') and d not in ('node_modules','.git','__pycache__','.pytest_cache','.vercel','dist-preview','tmp','.superpowers') and (rel/d).as_posix() not in ('data/workbench','data/processed','results','artifacts','reports')]
        for name in files:
            p=Path(folder)/name; path=p.relative_to(ROOT)
            if name=='SHA256SUMS.txt' or name.startswith('qa-preview') or p.is_symlink() or name=='.env' or (name.startswith('.env.') and name!='.env.example') or name.endswith(('.pyc','.log','.zip','.sqlite','.sqlite3','.sqlite3-shm','.sqlite3-wal')):
                continue
            if path.parts[0] in ('models',) and name!='.gitkeep':continue
            if path.parts[:2]==('data','raw') and name!='.gitkeep':continue
            selected.append((path,p.read_bytes()))
    selected.sort(key=lambda item:item[0].as_posix())
    checksums=''.join(hashlib.sha256(data).hexdigest()+'  '+path.as_posix()+'\n' for path,data in selected)
    output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path,data in selected:
            info=zipfile.ZipInfo(release_root+'/'+path.as_posix())
            info.compress_type=zipfile.ZIP_DEFLATED
            info.create_system=3
            info.external_attr=(0o100755 if path.suffix=='.sh' else 0o100644)<<16
            archive.writestr(info,data)
        archive.writestr(release_root+'/SHA256SUMS.txt',checksums)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert not any('/.env' in n and not n.endswith('/.env.example') for n in archive.namelist())
    print(f'{output.name}: {len(selected)+1} files, {output.stat().st_size:,} bytes; ZIP integrity verified.')
    print('SHA-256: '+hashlib.sha256(output.read_bytes()).hexdigest())

if __name__=='__main__':main()
