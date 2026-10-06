"""Metadata derived exclusively from the saved inventory of the real files."""
from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path

from pyproj import Transformer
from shapely import from_wkt, force_2d
from shapely.ops import transform

FIELDS = {
    'acquisition_start': 'zeroDopplerStartTime', 'acquisition_end': 'zeroDopplerEndTime',
    'granule_id': 'granuleId', 'product': 'productType', 'level': 'productLevel',
    'orbit_direction': 'orbitPassDirection', 'look_direction': 'lookDirection',
    'track': 'trackNumber', 'frame': 'frameNumber', 'orbit': 'absoluteOrbitNumber',
    'product_version': 'productVersion', 'doi': 'productDoi', 'footprint_wkt': 'boundingPolygon',
    'specification_version': 'productSpecificationVersion',
}


def parse_date(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def observation(audit, frequency='frequencyA', term='HHHH'):
    datasets = {d['path']: d for d in audit['datasets']}
    # Find the actual identification group by its datasets, rather than guessing a root.
    roots = {p.rsplit('/', 1)[0] for p in datasets if p.endswith('/zeroDopplerStartTime')
             and '/identification/' in p}
    if len(roots) != 1:
        raise ValueError('Cannot uniquely identify acquisition metadata')
    root = roots.pop()
    item = {'filename': audit['filename'], 'size_bytes': audit['size_bytes'], 'provisional': True,
            'identification_path':root}
    for field, name in FIELDS.items():
        path = root + '/' + name
        if path not in datasets or 'value' not in datasets[path]:
            raise ValueError(f'Missing required metadata: {path}')
        item[field] = datasets[path]['value']
    layers = [d for p, d in datasets.items() if p.endswith(f'/grids/{frequency}/{term}')]
    if len(layers) != 1:
        raise ValueError(f'Cannot uniquely identify {frequency}/{term}')
    layer = layers[0]
    grid = layer['path'].rsplit('/', 1)[0]
    item.update(layer_path=layer['path'], layer_dtype=layer['dtype'], shape=layer['shape'],
                layer_attributes=layer['attrs'], fillvalue=layer['fillvalue'], frequency=frequency,
                covariance_term=term, polarization=term[:2], grid_path=grid)
    for name in ['xCoordinates', 'yCoordinates', 'xCoordinateSpacing', 'yCoordinateSpacing',
                 'projection', 'listOfCovarianceTerms', 'mask', 'numberOfLooks']:
        if grid + '/' + name not in datasets:
            raise ValueError(f'Missing grid metadata {name}')
    item['crs'] = 'EPSG:' + str(datasets[grid + '/projection']['value'])
    item['spacing'] = [datasets[grid + '/xCoordinateSpacing']['value'],
                       datasets[grid + '/yCoordinateSpacing']['value']]
    item['origin_center'] = [datasets[grid + '/xCoordinates']['first'],
                             datasets[grid + '/yCoordinates']['first']]
    item['covariance_terms'] = datasets[grid + '/listOfCovarianceTerms']['value']
    item['bounds_wgs84'] = list(force_2d(from_wkt(item['footprint_wkt'])).bounds)
    return item


def compatibility(before, after):
    reasons = []
    days = (parse_date(after['acquisition_start']) - parse_date(before['acquisition_start'])).total_seconds()/86400
    if days < 1:
        reasons.append('Not distinct temporal observations (at least 24 hours required)')
    for key in ['product', 'level', 'track', 'frame', 'orbit_direction', 'look_direction',
                'product_version', 'frequency', 'covariance_term', 'crs', 'spacing', 'origin_center', 'shape']:
        if before[key] != after[key]:
            reasons.append(f'Incompatible {key}')
    if before['product'] != 'GCOV' or before['level'] != 'L2':
        reasons.append('Expected L2 GCOV')
    project = Transformer.from_crs('EPSG:4326', before['crs'], always_xy=True).transform
    first = transform(project, force_2d(from_wkt(before['footprint_wkt'])))
    second = transform(project, force_2d(from_wkt(after['footprint_wkt'])))
    overlap = first.intersection(second).area / min(first.area, second.area)
    if overlap < .8:
        reasons.append('Less than 80% footprint overlap')
    return {'accepted': not reasons, 'reasons': reasons, 'separation_days': days,
            'footprint_overlap_fraction': overlap, 'before': before['filename'], 'after': after['filename']}


def build_inventory(audit_path, frequency='frequencyA', term='HHHH'):
    audits = json.loads(Path(audit_path).read_text())
    items = [observation(a, frequency, term) for a in audits]
    items.sort(key=lambda x: (x['acquisition_start'], x['filename']))
    groups = {}
    for item in items:
        key = f"{item['acquisition_start']} / track {item['track']} / frame {item['frame']}"
        groups.setdefault(key, []).append(item['filename'])
    pairs = [compatibility(a,b) for a,b in combinations(items,2)]
    return {'observations': items, 'same_observation_groups': groups, 'pair_checks': pairs}
