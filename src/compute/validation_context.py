"""Compare nominal candidates with independently mapped August 2026 impacts."""
import hashlib
import json
import struct
from pathlib import Path
from zipfile import ZipFile

from pyproj import Transformer
from shapely.geometry import Polygon, shape
from shapely.ops import transform, unary_union

from src.export.artifacts import write_json

SOURCE_URL = ('https://ihp-wins.unesco.org/en/dataset/'
              'nepal-satellite-detected-mudflow-and-rockflow-extent-nepal')
DOWNLOAD_URL = ('https://ihp-wins.unesco.org/dataset/'
                '054c3516-e2b8-49a4-a256-1de4b7431ec6/resource/'
                '9f9498b2-4b48-4e83-8c8c-b227d5938a08/download/'
                'floodextent_20260826_nepal.zip')
EXPECTED_SHA256 = '867b5bebb4881d1b8f88af31df7f784f5db612fa651c911d81d7304bf5be0dda'
SOURCE_ID = 'UNOSAT_20260826_MUDFLOW_EXTENT'
ALLOWED = {'SUPPORTED', 'PARTIALLY_SUPPORTED', 'UNVERIFIED', 'CONTRADICTED'}


def shapefile_rings(content):
    """Read the polygon rings of the archived official SHP without extra GIS packages."""
    if struct.unpack_from('<i', content, 32)[0] != 5:
        raise ValueError('Official source is not a polygon shapefile')
    offset = 100
    rings = []
    while offset < len(content):
        _, words = struct.unpack_from('>ii', content, offset)
        offset += 8
        record = content[offset:offset + 2 * words]
        offset += 2 * words
        if struct.unpack_from('<i', record)[0] != 5:
            raise ValueError('Unexpected shapefile record type')
        part_count, point_count = struct.unpack_from('<ii', record, 36)
        starts = struct.unpack_from('<' + 'i' * part_count, record, 44)
        point_start = 44 + part_count * 4
        points = [struct.unpack_from('<dd', record, point_start + 16 * i)
                  for i in range(point_count)]
        for i, start in enumerate(starts):
            end = starts[i + 1] if i + 1 < part_count else point_count
            rings.append(Polygon(points[start:end]))
    if not rings or any(not ring.is_valid for ring in rings):
        raise ValueError('Invalid or empty official polygon rings')
    return rings


def official_extent(archive_path):
    content = Path(archive_path).read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError('Independent extent checksum differs from reviewed source')
    with ZipFile(archive_path) as archive:
        names = [n for n in archive.namelist() if n.lower().endswith('.shp')]
        if len(names) != 1:
            raise ValueError('Expected one official SHP file')
        rings = shapefile_rings(archive.read(names[0]))
    # Union is sufficient for an overlap screen. No nominal region intersects
    # any source ring; this result is unaffected by possible multipart holes.
    return unary_union(rings), digest, len(rings)


def compute(case_dir, archive_path='data/context/unosat_20260826_flood_extent.zip'):
    case_dir = Path(case_dir)
    evidence = json.loads((case_dir / 't1_t3/evidence.json').read_text())
    nominal = json.loads((case_dir / 't1_t3/change_regions.geojson').read_text())
    extent, digest, ring_count = official_extent(archive_path)
    source = {'id': SOURCE_ID, 'publisher': 'UNOSAT / UNITAR via UNESCO IHP-WINS',
              'title': 'Satellite-detected mudflow and rockflow extent in Rasuwa and Nuwakot',
              'event_date_utc': '2026-08-26',
              'image_dates_utc': ['2026-08-26', '2026-08-27'],
              'publication_date_utc': '2026-08-28', 'url': SOURCE_URL,
              'download_url': DOWNLOAD_URL, 'doi': '10.63253/1y26ihdq',
              'local_archive': str(archive_path), 'archive_sha256': digest,
              'source_crs': 'EPSG:32645', 'polygon_ring_count': ring_count,
              'field_validated': False,
              'what_it_shows': 'Preliminary satellite-mapped mudflow and rockflow extent following the 26 August Rasuwa/Nuwakot flood.',
              'what_it_does_not_prove': 'It does not identify the cause of NISAR backscatter changes outside its mapped polygons, or establish no impact outside its analyzed area.'}
    by_id = {feature['properties']['id']: feature for feature in nominal['features']}
    ranked = sorted(evidence['regions'],
                    key=lambda r: (-r['area_km2'], -abs(r['median_change_db']), r['id']))
    top_ids = {r['id'] for r in ranked[:10]}
    project = Transformer.from_crs('EPSG:4326', 'EPSG:32645', always_xy=True).transform
    records = []
    validated_features = []
    for region in ranked:
        feature = by_id[region['id']]
        projected = transform(project, shape(feature['geometry']))
        overlap_km2 = projected.intersection(extent).area / 1e6
        reviewed = region['id'] in top_ids
        # Spatial overlap alone would support only event context. This source
        # has zero overlap with all nominal regions, so no status is upgraded.
        status = 'UNVERIFIED'
        record = {'region_id': region['id'], 'rank': ranked.index(region) + 1,
                  'reviewed': reviewed, 'validation_status': status,
                  'area_km2': region['area_km2'],
                  'source_id': SOURCE_ID if reviewed else None,
                  'source_date_utc': source['event_date_utc'] if reviewed else None,
                  'source_url': SOURCE_URL if reviewed else None,
                  'source_overlap_km2': overlap_km2,
                  'what_source_shows': source['what_it_shows'] if reviewed else None,
                  'what_source_does_not_prove': source['what_it_does_not_prove'] if reviewed else None,
                  'review_notes': ('No polygon overlap with the independently mapped 26 August impact extent; '
                                   'the source cannot validate this candidate or its cause.' if reviewed
                                   else 'Not prioritized for individual independent-source review.'),
                  'cause_status': 'UNVERIFIED'}
        records.append(record)
        copied = json.loads(json.dumps(feature))
        copied['properties'].update({'validation_status': status, 'validation_reviewed': reviewed,
                                     'source_overlap_km2': overlap_km2})
        validated_features.append(copied)
    if set(by_id) != {r['region_id'] for r in records}:
        raise ValueError('Validation geometry differs from nominal regions')
    report = {'case_id': evidence['case_id'], 'reference_pair': 't1_t3',
              'source': source, 'method': 'Exact polygon intersection in EPSG:32645; top 10 ranked by nominal area then absolute median signed change.',
              'source_screening': {'reviewed_region_count': len(top_ids),
                                   'nominal_region_count': len(records),
                                   'region_count_with_polygon_overlap': sum(r['source_overlap_km2'] > 0 for r in records),
                                   'interpretation': 'No overlap does not imply no change; source mapping covers a different event footprint and is preliminary.'},
              'optical_catalog': 'data/context/sentinel2_catalog_screening.json',
              'optical_limit': 'Sentinel-2 tile metadata screened; image pixels and per-region cloud masks not inspected.',
              'allowed_statuses': sorted(ALLOWED), 'regions': records,
              'validation_status': 'UNVERIFIED'}
    write_json(case_dir / 'validation.json', report)
    write_json(case_dir / 'validated_regions.geojson',
               {'type': 'FeatureCollection', 'features': validated_features})
    return report


if __name__ == '__main__':
    result = compute('data/derived/nepal_case_01')
    print('Independent source screen:', result['source_screening'])
