"""Discover local GCOV observations and select a physically compatible repeat series."""
import os
from pathlib import Path

import h5py

from src.ingest.inspect_h5 import inspect, native
from src.ingest.metadata import observation, parse_date

PHYSICAL_KEYS = ('product', 'level', 'track', 'frame', 'orbit_direction',
                 'look_direction', 'product_version', 'frequency', 'covariance_term',
                 'range_bandwidth_hz', 'center_frequency_hz', 'source_polarizations', 'dithered')


def read_observation(path, frequency='frequencyA', term='HHHH'):
    with h5py.File(path, 'r') as source:
        roots = []
        def find(name, obj):
            if isinstance(obj, h5py.Dataset) and name.endswith('/identification/productType'):
                roots.append('/' + name.rsplit('/', 1)[0])
        source.visititems(find)
        if len(roots) != 1 or native(source[roots[0] + '/productType'][()]) != 'GCOV':
            raise ValueError('Not a geocoded GCOV product; L0 data require a different processor')
    audit = inspect(path)
    item = observation(audit, frequency, term)
    datasets = {d['path']: d for d in audit['datasets']}
    swath = item['grid_path'].split('/grids/')[0] + '/metadata/sourceData/swaths/' + frequency
    for field, suffix in [('range_bandwidth_hz', 'acquiredRangeBandwidth'),
                          ('center_frequency_hz', 'centerFrequency'),
                          ('source_polarizations', 'listOfPolarizations')]:
        key = swath + '/' + suffix
        if key not in datasets or 'value' not in datasets[key]:
            raise ValueError(f'Missing physical comparability metadata: {key}')
        item[field] = datasets[key]['value']
    item['source_polarizations'] = sorted(item['source_polarizations'])
    key = item['identification_path'] + '/isDithered'
    if key not in datasets:
        raise ValueError('Missing dithered acquisition flag')
    item['dithered'] = datasets[key]['value']
    item['named_datatypes'] = audit.get('named_datatypes', [])
    return item


def incompatibilities(anchor, candidate):
    """Geocoding alone does not make different tracks or radar modes comparable."""
    reasons = [f'Incompatible {key}: {candidate.get(key)!r} (anchor {anchor.get(key)!r})'
               for key in PHYSICAL_KEYS if candidate.get(key) != anchor.get(key)]
    if candidate['product'] != 'GCOV' or candidate['level'] != 'L2':
        reasons.append('Expected L2 GCOV')
    return reasons


def select_series(records, anchor_source):
    anchor = next((r for r in records if r['source_file'] == anchor_source), None)
    if anchor is None:
        raise ValueError('Anchor source absent from readable inventory')
    selected = []
    seen = set()
    for record in sorted(records, key=lambda r: (parse_date(r['acquisition_start']),
                                                  r['source_file'] != anchor_source, r['source_file'])):
        reasons = incompatibilities(anchor, record)
        timestamp = parse_date(record['acquisition_start'])
        if not reasons and timestamp in seen:
            reasons.append('Duplicate observation timestamp in the selected series')
        record['selection_reasons'] = reasons
        record['selected'] = not reasons
        if not reasons:
            seen.add(timestamp)
            selected.append(record)
    if len(selected) < 3:
        raise ValueError('At least three physically compatible distinct acquisitions are required')
    for first, second in zip(selected, selected[1:]):
        if (parse_date(second['acquisition_start']) - parse_date(first['acquisition_start'])).total_seconds() < 86400:
            raise ValueError('Selected timestamps are not distinct repeat-day observations')
    return selected


def discover(scan_root, anchor_source, frequency='frequencyA', term='HHHH'):
    files = []
    for root, directories, names in os.walk(Path(scan_root).resolve()):
        directories[:] = [name for name in directories
                          if not name.startswith('.') and name not in {'node_modules', '__pycache__'}]
        files.extend(Path(root) / name for name in names if name.endswith('.h5'))
    files.sort()
    records = []
    failures = []
    for path in files:
        relative = os.path.relpath(path, Path.cwd())
        try:
            record = read_observation(path, frequency, term)
            record['source_file'] = relative
            records.append(record)
        except (OSError, ValueError, KeyError) as error:
            failures.append({'source_file': relative, 'selected': False,
                             'selection_reasons': [str(error)]})
    selected = select_series(records, anchor_source)
    groups = {}
    for item in records:
        key = tuple(str(item[k]) for k in PHYSICAL_KEYS)
        groups.setdefault(key, []).append(item)
    catalog = [{'track': group[0]['track'], 'frame': group[0]['frame'],
                'range_bandwidth_hz': group[0]['range_bandwidth_hz'],
                'center_frequency_hz': group[0]['center_frequency_hz'],
                'product_version': group[0]['product_version'],
                'timestamps': sorted({item['acquisition_start'] for item in group}),
                'observation_count': len({item['acquisition_start'] for item in group}),
                'source_files': [item['source_file'] for item in group]} for group in groups.values()]
    return {'anchor_source': anchor_source, 'records': records, 'unreadable_or_unsupported': failures,
            'compatible_groups': catalog,
            'file_count': len(files), 'selected_source_files': [r['source_file'] for r in selected]}, selected
