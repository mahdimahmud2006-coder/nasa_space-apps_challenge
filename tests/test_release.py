import hashlib
import json
from pathlib import Path
from src.api.readiness import readiness
from scripts.verify_release import verify
from scripts.package_release import files


def test_readiness_reports_missing_runtime_without_fabricating_ready(tmp_path):
    result=readiness(tmp_path)
    assert not result['runtime_ready'] and result['missing_runtime_files']
    assert result['landslide_validation_status']=='UNAVAILABLE'


def test_release_hash_verifier_detects_tampering(tmp_path):
    (tmp_path/'asset').write_bytes(b'original')
    (tmp_path/'RELEASE_MANIFEST.json').write_text(json.dumps({'files_sha256':{'asset':hashlib.sha256(b'original').hexdigest()}}))
    assert verify(tmp_path)['verified']
    (tmp_path/'asset').write_bytes(b'changed');assert not verify(tmp_path)['verified']


def test_package_allowlist_excludes_credentials_raw_satellites_and_git(tmp_path):
    (tmp_path/'web').mkdir();(tmp_path/'web/index.html').write_text('page')
    (tmp_path/'.env').write_text('sensitive');(tmp_path/'raw.h5').write_bytes(b'raw')
    (tmp_path/'.git').mkdir();(tmp_path/'.git/config').write_text('git')
    names={str(p.relative_to(tmp_path)) for p in files(tmp_path)}
    assert 'web/index.html' in names
    assert not any(name in names for name in ['.env','raw.h5','.git/config'])
