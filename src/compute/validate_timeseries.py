"""Validate actual COG pixels, time ordering, scores, tracking and Parquet evidence."""
import argparse
import hashlib
import json
from pathlib import Path

from affine import Affine
import numpy as np
import pyarrow.parquet as pq
from pyproj import Transformer
import rasterio
from shapely.geometry import shape
from shapely.ops import transform

from src.compute.area import pixel_area_km2
from src.compute.time_series import interval_candidates, persistence, fixed_zones, zone_metrics
from src.ingest.metadata import parse_date


def require(value, message):
    if not value:
        raise ValueError(message)


def validate(directory=Path('data/derived/nepal_case_01/timeseries'), check_historical=False):
    directory = Path(directory)
    timeline = json.loads((directory / 'timeline.json').read_text())
    observations = timeline['observations']
    require(len(observations) >= 3, 'Fewer than three aligned observations')
    timestamps = [parse_date(o['timestamp']) for o in observations]
    require(all(b > a for a, b in zip(timestamps, timestamps[1:])), 'Observation ordering failed')
    require(len({o['source_granule_id'] for o in observations}) == len(observations), 'Duplicate acquisition')
    physical = ('track', 'frame', 'polarization', 'product_version', 'range_bandwidth_hz', 'center_frequency_hz')
    for field in physical:
        require(len({str(o[field]) for o in observations}) == 1, f'Mixed physical source field {field}')
    grid = timeline['canonical_grid']
    affine = Affine(*grid['affine'])
    pixel_area = pixel_area_km2(affine, grid['crs'])
    require(np.isclose(pixel_area, grid['pixel_area_km2']), 'Projected area mismatch')

    def read(name):
        with rasterio.open(directory / name) as ds:
            require(ds.transform == affine and str(ds.crs) == grid['crs'] and
                    [ds.height, ds.width] == grid['shape'], f'Canonical grid mismatch: {name}')
            require(ds.tags(ns='IMAGE_STRUCTURE').get('LAYOUT') == 'COG', f'Not a GDAL COG: {name}')
            return ds.read(1)

    arrays = [read(o['processed_raster']) for o in observations]
    for obs, image in zip(observations, arrays):
        require(np.isclose(np.isfinite(image).mean(), obs['valid_fraction']), 'Observation validity mismatch')
        require(hashlib.sha256(image.tobytes()).hexdigest() == obs['quality']['processed_sha256'], 'Processed data fingerprint mismatch')
        require(Path(obs['source_file']).stat().st_size == obs['source_size_bytes'], 'Source size changed since extraction')
    masks = []
    raw_masks = []
    valid = []
    for i, interval in enumerate(timeline['intervals']):
        change = read(interval['change_raster'])
        np.testing.assert_allclose(change, arrays[i + 1] - arrays[i], rtol=0, atol=0, equal_nan=True)
        score, raw, labels, stats = interval_candidates(change, interval['threshold'],
                        timeline['cleanup']['min_region_pixels'], timeline['cleanup']['opening_iterations'], timeline['epsilon'])
        np.testing.assert_allclose(read(interval['score_raster']), score, rtol=0, atol=0, equal_nan=True)
        saved = read(interval['mask_raster'])
        require(np.array_equal(saved == 255, ~np.isfinite(change)), 'Interval nodata mismatch')
        require(np.array_equal(saved == 1, labels > 0), 'Interval cleanup differs from saved rule')
        require(np.isclose(np.count_nonzero(labels) * pixel_area, interval['candidate_area_km2']), 'Interval area mismatch')
        require(int(labels.max()) == interval['region_count'], 'Interval region count mismatch')
        require(stats == interval['normalization'], 'Normalization parameters mismatch')
        require(interval['before'] == observations[i]['observation_id'] and
                interval['after'] == observations[i + 1]['observation_id'], 'Interval source mismatch')
        masks.append(labels > 0); raw_masks.append(raw); valid.append(np.isfinite(change))
    require(len(timeline['intervals']) == len(observations) - 1, 'Successive interval count mismatch')
    strict, available, count = persistence(raw_masks, valid)
    retained, _, _ = persistence(masks, valid)
    for name, expected in [('persistence.tif', strict), ('persistence_available.tif', available),
                           ('valid_interval_count.tif', count), ('candidate_persistence.tif', retained)]:
        np.testing.assert_allclose(read(name), expected, rtol=0, atol=0, equal_nan=True)
    labels = read('zone_labels.tif')
    require(np.array_equal(labels, fixed_zones(masks)), 'Zone footprint differs from connected interval union')
    zones, rows, recovery = zone_metrics(labels, arrays, masks, valid, observations, pixel_area,
                timeline['series_key'], timeline['minimum_zone_common_fraction'], timeline['epsilon'])
    recorded = json.loads((directory / 'zones.json').read_text())
    for calculated, saved in zip(zones, recorded):
        require(all(saved[key] == value for key, value in calculated.items()), 'Zone measurements or ID mismatch')
    require(len(zones) == len(recorded), 'Zone count mismatch')
    require(rows == json.loads((directory / 'zone_timeseries.json').read_text()), 'Zone time series mismatch')
    require(pq.read_table(directory / 'zone_timeseries.parquet').to_pylist() == rows, 'Parquet/JSON measurements differ')
    np.testing.assert_allclose(read('recovery.tif'), recovery, rtol=0, atol=0, equal_nan=True)
    geo = json.loads((directory / 'zones.geojson').read_text())
    require({f['properties']['zone_id'] for f in geo['features']} == {z['zone_id'] for z in zones}, 'GeoJSON zone IDs mismatch')
    project = Transformer.from_crs(4326, grid['crs'], always_xy=True).transform
    area = sum(transform(project, shape(f['geometry'])).area for f in geo['features']) / 1e6
    require(np.isclose(area, np.count_nonzero(labels) * pixel_area, rtol=.002, atol=1e-5), 'Zone vector/native area mismatch')
    require(all(shape(f['geometry']).is_valid for f in geo['features']), 'Invalid zone geometry')
    require(all(z['validation_status'] == 'UNVERIFIED' for z in recorded), 'Unsupported cause upgrade')
    public = Path('web/public/cases') / timeline['case_id'] / 'timeseries'
    for path in directory.iterdir():
        if path.suffix in {'.json', '.geojson', '.png', '.webp', '.parquet'}:
            require(path.read_bytes() == (public / path.name).read_bytes(), 'Public artifact differs: ' + path.name)
    snapshot = Path('docs/reports/imp02-legacy-before.json')
    if check_historical:
        require(snapshot.exists(), 'Historical snapshot is unavailable')
        for path, digest in json.loads(snapshot.read_text()).items():
            require(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, 'Legacy artifact modified: ' + path)
        print(f'PASS: all {len(json.loads(snapshot.read_text()))} historical artifacts remain byte-identical to the saved snapshot')
    print(f"PASS time series: {len(observations)} aligned COGs, {len(masks)} successive intervals, {len(zones)} zones")
    print('PASS scores, nodata, persistence denominators, recovery, native/vector areas, Parquet and public copies')
    return timeline


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', default='data/derived/nepal_case_01/timeseries')
    parser.add_argument('--check-historical', action='store_true',
                        help='Also compare archived implementation-01 bytes; intentional later regeneration may differ')
    args = parser.parse_args()
    validate(Path(args.directory), args.check_historical)
