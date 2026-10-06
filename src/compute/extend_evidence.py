"""Build descriptive temporal, robustness and independent-context artifacts."""
import json
import shutil
from pathlib import Path

from src.compute.robust_core import compute_pair
from src.compute.temporal_consistency import compute as compute_temporal
from src.compute.validation_context import compute as compute_validation
from src.export.artifacts import write_json


def run(case_dir='data/derived/nepal_case_01'):
    case_dir = Path(case_dir)
    pair_ids = ('t1_t2', 't1_t3', 't2_t3')
    temporal = compute_temporal(case_dir)
    robust = {pair: compute_pair(case_dir / pair) for pair in pair_ids}
    validation = compute_validation(case_dir)
    temporal_by_id = {r['region_id']: r for r in temporal['regions']}
    validation_by_id = {r['region_id']: r for r in validation['regions']}
    manifest_path = case_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['default_pair'] = 't1_t3'
    manifest['additional_evidence'] = {'temporal_consistency': 'temporal_consistency.json',
                                       'validation': 'validation.json'}
    for pair in manifest['pairs']:
        pair_id = pair['id']
        path = case_dir / pair_id / 'evidence.json'
        evidence = json.loads(path.read_text())
        core_by_id = {r['region_id']: r for r in robust[pair_id]['regions']}
        for region in evidence['regions']:
            region_id = region['id']
            region['robust_core'] = core_by_id.get(region_id)
            region['temporal_consistency'] = (temporal_by_id[region_id] if pair_id == 't1_t3' else None)
            region['validation'] = (validation_by_id[region_id] if pair_id == 't1_t3' else
                                    {'validation_status': 'UNVERIFIED', 'reviewed': False,
                                     'review_notes': 'Independent-source review prioritized the 24-day comparison.'})
            region['validation_status'] = 'UNVERIFIED'
        evidence['robust_core'] = {'path': 'robust_core.json', **robust[pair_id]['summary'],
                                   'strict_threshold_db': robust[pair_id]['strict_threshold_db']}
        evidence['validation_status'] = 'UNVERIFIED'
        if pair_id == 't1_t3':
            evidence['temporal_summary'] = temporal['class_counts']
            evidence['independent_validation'] = validation['source_screening']
        write_json(path, evidence)
        pair['robust_core_summary'] = robust[pair_id]['summary']
    write_json(manifest_path, manifest)
    public = Path('web/public/cases') / manifest['case_id']
    for path in sorted(case_dir.rglob('*')):
        if path.is_file() and path.suffix in {'.json', '.geojson', '.csv', '.webp', '.png'}:
            target = public / path.relative_to(case_dir)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    return manifest


if __name__ == '__main__':
    result = run()
    print(f"Evidence extension exported for {len(result['pairs'])} pairs; default {result['default_pair']}")
