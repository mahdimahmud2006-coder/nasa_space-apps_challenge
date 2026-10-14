"""Build a self-contained local-runtime release with explicit file hashes and no raw HDF5/secrets."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.api.readiness import readiness

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def files(root):
    # Explicit allowlist: no home folders, environment files, Git metadata or raw granules.
    paths=[]
    for folder in ['src','web','tests','docs']:
        paths.extend(p for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.zip') and p.name!='release_package_qa.json')
    paths.extend(p for p in root.glob('config*.json') if p.is_file())
    for name in ['README.md','LICENSE','requirements.txt','pyproject.toml','Makefile','run.sh','scripts/package_release.py','scripts/verify_release.py','scripts/check_web.py']:
        paths.append(root/name)
    # Runtime counterfactuals use this local component cube, not raw satellites or live APIs.
    for name in ['manifest.json','model.json','components.npz']:
        paths.append(root/'data/derived/nepal_case_01/flood'/name)
    paths.extend((root/'data/derived/nepal_case_01/flood/scenarios').glob('*/result.json'))
    return sorted(set(paths))


def build(root=ROOT):
    root=Path(root);status=readiness(root)
    if not status['runtime_ready']:raise RuntimeError('Cannot package an incomplete local runtime')
    paths=files(root);records={str(p.relative_to(root)):digest(p) for p in paths}
    manifest={'project':status,'files_sha256':records,'packaging_scope':'Local application and analytical viewer assets, with the flood runtime component cube. Raw NISAR, NASADEM/Landsat source caches and full offline source reprocessing inputs are not bundled.',
        'scientific_reproduction':'Full-source validators and rebuilding require the separately retained source datasets described in DATASETS.md; runtime integrity can be checked with scripts/verify_release.py.',
        'no_credentials_bundled':True}
    directory=root/'dist';directory.mkdir(exist_ok=True);target=directory/f'terrapulse-{status["version"]}.zip';temporary=target.with_suffix('.zip.tmp')
    def write(archive,name,content,mode=0o644):
        info=zipfile.ZipInfo(name,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=(0o100000|mode)<<16
        archive.writestr(info,content,compresslevel=6)
    with zipfile.ZipFile(temporary,'w') as archive:
        for path in paths:
            content=path.read_bytes();name=str(path.relative_to(root))
            if hashlib.sha256(content).hexdigest()!=records[name]:raise RuntimeError('Source changed while packaging: '+name)
            write(archive,name,content,0o755 if path.name=='run.sh' else 0o644)
        write(archive,'RELEASE_MANIFEST.json',(json.dumps(manifest,indent=2)+'\n').encode())
    with zipfile.ZipFile(temporary) as archive:assert archive.testzip() is None
    temporary.replace(target);archive_digest=digest(target)
    (directory/(target.name+'.sha256')).write_text(archive_digest+'  '+target.name+'\n')
    print(json.dumps({'archive':str(target),'files':len(paths),'bytes':target.stat().st_size,'sha256':archive_digest},indent=2))
    return target


if __name__=='__main__':build()
