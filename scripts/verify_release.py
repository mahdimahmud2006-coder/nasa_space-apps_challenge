"""Verify a release's exact runtime files with only the Python standard library."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(root):
    root=Path(root).resolve();manifest=json.loads((root/'RELEASE_MANIFEST.json').read_text());problems=[]
    for filename,expected in manifest['files_sha256'].items():
        path=(root/filename).resolve()
        if not path.is_relative_to(root):raise ValueError('Invalid release manifest path')
        if not path.is_file():problems.append('Missing: '+filename);continue
        with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
        if actual!=expected:problems.append('Hash mismatch: '+filename)
    return {'verified':not problems,'files_checked':len(manifest['files_sha256']),'problems':problems,
        'scope':'Packaged source and runtime integrity, not independent scientific or browser validation'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args();result=verify(args.root);print(json.dumps(result,indent=2));raise SystemExit(0 if result['verified'] else 1)
