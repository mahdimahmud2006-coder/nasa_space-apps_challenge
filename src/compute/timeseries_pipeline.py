"""Reproduce a compatible local NISAR time series without altering legacy nominal outputs."""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import shutil
import tempfile
import sys

from affine import Affine
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.shutil import copy as copy_raster
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import Window, from_bounds, transform as window_transform

from src.compute.area import pixel_area_km2
from src.compute.pipeline import code_hash
from src.compute.preprocess import median_db
from src.compute.regions import region_statistics
from src.compute.time_series import interval_candidates, persistence, fixed_zones, zone_metrics
from src.export.artifacts import write_json, raster, preview, overlay, vectorize, display_regions
from src.ingest.extract_gcov import analysis_window, extract
from src.ingest.metadata import parse_date
from src.ingest.timeseries import discover


def cog(path, array, affine, crs, description, nodata=np.nan, categorical=False):
    """Use GDAL's COG driver, which creates tiled storage and internal overviews."""
    with tempfile.TemporaryDirectory(prefix='terrapulse-cog-') as tmp:
        source = Path(tmp) / 'source.tif'
        raster(source, array, affine, crs, nodata, description)
        copy_raster(source, path, driver='COG', BLOCKSIZE=256, COMPRESS='DEFLATE',
                    OVERVIEW_RESAMPLING='NEAREST' if categorical else 'AVERAGE',
                    BIGTIFF='IF_SAFER')


def canonical_observation(source, affine, crs, shape, median_size):
    dx, dy = source['spacing']
    if dx <= 0 or dy >= 0:
        raise ValueError('Source must have a regular north-up grid')
    x, y = source['origin_center']
    full = Affine(dx, 0, x - dx / 2, 0, dy, y - dy / 2)
    height, width = shape
    bounds = rasterio.transform.array_bounds(height, width, affine)
    source_bounds = transform_bounds(crs, source['crs'], *bounds, densify_pts=21)
    floating = from_bounds(*source_bounds, transform=full)
    if (floating.row_off < -1e-6 or floating.col_off < -1e-6 or
            floating.row_off + floating.height > source['shape'][0] + 1e-6 or
            floating.col_off + floating.width > source['shape'][1] + 1e-6):
        raise ValueError(f"Canonical area is outside {source['source_file']}")
    window = floating.round_offsets().round_lengths()
    exact = (window_transform(window, full) == affine and source['crs'] == crs
             and (int(window.height), int(window.width)) == tuple(shape))
    if not exact:
        halo = median_size // 2 + 1
        row = max(0, math.floor(floating.row_off) - halo)
        col = max(0, math.floor(floating.col_off) - halo)
        end_row = min(source['shape'][0], math.ceil(floating.row_off + floating.height) + halo)
        end_col = min(source['shape'][1], math.ceil(floating.col_off + floating.width) + halo)
        window = Window(col, row, end_col - col, end_row - row)
    raw, quality = extract(Path(source['source_file']), source, window)
    filtered = median_db(raw, median_size)
    native_affine = window_transform(window, full)
    if native_affine == affine and source['crs'] == crs and filtered.shape == tuple(shape):
        result = filtered
        quality['alignment'] = 'exact native grid extraction; no reprojection'
    else:
        result = np.full(shape, np.nan, dtype=np.float32)
        reproject(filtered, result, src_transform=native_affine, src_crs=source['crs'],
                  dst_transform=affine, dst_crs=crs, src_nodata=np.nan, dst_nodata=np.nan,
                  resampling=Resampling.bilinear)
        coverage = np.zeros(shape, dtype=np.float32)
        reproject(np.isfinite(filtered).astype(np.float32), coverage,
                  src_transform=native_affine, src_crs=source['crs'],
                  dst_transform=affine, dst_crs=crs, resampling=Resampling.bilinear,
                  dst_nodata=0)
        result[coverage < 1 - 1e-6] = np.nan
        quality['alignment'] = 'bilinear reprojection to canonical grid; full contributing validity required'
    quality['analysis_valid_pixels'] = int(np.isfinite(result).sum())
    quality['processed_sha256'] = hashlib.sha256(result.tobytes()).hexdigest()
    return result, quality


def threshold_setting(config, legacy):
    path = config.get('threshold_validation_file')
    if path:
        record = json.loads(Path(path).read_text())
        if record.get('calibration_status') != 'VALIDATED' or not record.get('validation_source'):
            raise ValueError('A validated threshold needs a validation source and VALIDATED status')
        if record.get('metric') != 'centered_successive_delta_mad_z':
            raise ValueError('Threshold calibration does not describe this score metric')
        tau = float(record['threshold'])
        return tau, record
    tau = float(legacy['change']['threshold_value'])
    return tau, {'threshold': tau, 'calibration_status': 'UNCALIBRATED',
                 'metric': 'centered_successive_delta_mad_z', 'validation_source': None,
                 'basis': 'existing legacy multiplier, retained as an exploratory setting only',
                 'interpretation': 'candidate anomaly; statistical significance is not established'}


def parquet_rows(path, rows):
    schema = pa.schema([
        ('zone_id', pa.string()), ('observation_id', pa.string()), ('timestamp', pa.string()),
        ('area_km2', pa.float64()), ('zone_footprint_area_km2', pa.float64()),
        ('common_valid_fraction', pa.float64()), ('mean_delta_from_baseline_db', pa.float64()),
        ('median_delta_from_baseline_db', pa.float64()), ('mean_absolute_delta_from_baseline_db', pa.float64()),
        ('recovery', pa.float64()), ('validation_status', pa.string())])
    pq.write_table(pa.Table.from_pylist(rows, schema=schema), path, compression='zstd')


def run(config_path='config.timeseries.json'):
    config = json.loads(Path(config_path).read_text())
    legacy = json.loads(Path(config['legacy_config']).read_text())
    directory = Path('data/derived') / config['case_id'] / 'timeseries'
    directory.mkdir(parents=True, exist_ok=True)
    # Inventory all supplied local dates, including products incompatible with this series.
    audit, selected = discover(config['scan_root'], config['anchor_source'],
                               config['frequency'], config['covariance_term'])
    write_json(directory / 'source_audit.json', audit)
    anchor = next(r for r in selected if r['source_file'] == config['anchor_source'])
    _, affine = analysis_window(anchor, legacy['aoi_center_wgs84'], legacy['aoi_size_m'])
    shape = (round(legacy['aoi_size_m'][1] / abs(anchor['spacing'][1])),
             round(legacy['aoi_size_m'][0] / anchor['spacing'][0]))
    crs = anchor['crs']
    pixel_area = pixel_area_km2(affine, crs)
    arrays = []
    observations = []
    for i, source in enumerate(selected, 1):
        print(f"Time series: extracting {source['source_file']}", flush=True)
        image, quality = canonical_observation(source, affine, crs, shape,
                                                legacy['change']['median_filter_size'])
        fraction = float(np.isfinite(image).mean())
        if fraction < config['minimum_valid_fraction']:
            raise ValueError(f"Insufficient canonical AOI coverage in {source['source_file']}: {fraction:.3f}")
        arrays.append(image)
        timestamp = parse_date(source['acquisition_start']).isoformat().replace('+00:00', 'Z')
        date_id = timestamp[:10].replace('-', '_')
        observations.append({'observation_id': 'nisar_gc_' + date_id, 'timestamp': timestamp,
                             'dataset': 'NISAR_L2_GCOV_PROVISIONAL_V1', 'polarization': source['polarization'],
                             'track': source['track'], 'frame': source['frame'],
                             'orbit_direction': source['orbit_direction'], 'look_direction': source['look_direction'],
                             'source_file': source['source_file'], 'source_granule_id': source['granule_id'],
                             'source_size_bytes': source['size_bytes'],
                             'product_version': source['product_version'], 'doi': source['doi'],
                             'hdf5_path': source['layer_path'], 'range_bandwidth_hz': source['range_bandwidth_hz'],
                             'center_frequency_hz': source['center_frequency_hz'], 'valid_fraction': fraction,
                             'processed_raster': f'nisar_t{i}.tif', 'preview': f'nisar_t{i}.webp',
                             'quality': quality})
        cog(directory / f'nisar_t{i}.tif', image, affine, crs, 'validity-safe median gamma-0 HH backscatter (dB)')
    shared = np.concatenate([image[np.isfinite(image)][::16] for image in arrays])
    limits = np.percentile(shared, [2, 98]).tolist()
    for image, obs in zip(arrays, observations):
        preview(directory / obs['preview'], image, limits)
    tau, calibration = threshold_setting(config, legacy)
    epsilon = config['epsilon']
    params = legacy['change']
    intervals = []
    raw_masks = []
    masks = []
    valid = []
    for i in range(1, len(arrays)):
        change = arrays[i] - arrays[i - 1]
        score, raw_mask, labels, normalization = interval_candidates(change, tau, params['min_region_pixels'],
                                                                     params['opening_iterations'], epsilon)
        pair_id = f't{i}_t{i + 1}'
        good = np.isfinite(change)
        regions = region_statistics(labels, change, affine, crs)
        interval = {'interval_id': pair_id, 'before': observations[i - 1]['observation_id'],
                    'after': observations[i]['observation_id'],
                    'start': observations[i - 1]['timestamp'], 'end': observations[i]['timestamp'],
                    'days': (parse_date(observations[i]['timestamp']) - parse_date(observations[i - 1]['timestamp'])).total_seconds() / 86400,
                    'candidate_area_km2': int(np.count_nonzero(labels)) * pixel_area,
                    'raw_score_area_km2': int(raw_mask.sum()) * pixel_area,
                    'region_count': len(regions), 'common_valid_area_km2': int(good.sum()) * pixel_area,
                    'valid_fraction': float(good.mean()),
                    'median_signed_change_db': float(np.median(change[good])),
                    'median_absolute_change_db': float(np.median(np.abs(change[good]))),
                    'mean_absolute_change_db': float(np.mean(np.abs(change[good]))),
                    'candidate_median_absolute_change_db': float(np.median(np.abs(change[labels > 0]))) if np.any(labels) else None,
                    'normalization': normalization, 'threshold': tau,
                    'calibration_status': calibration['calibration_status'],
                    'change_raster': f'change_{pair_id}.tif', 'score_raster': f'score_{pair_id}.tif',
                    'mask_raster': f'candidate_{pair_id}.tif', 'overlay': f'{pair_id}_overlay.png'}
        intervals.append(interval)
        raw_masks.append(raw_mask)
        masks.append(labels > 0)
        valid.append(good)
        cog(directory / interval['change_raster'], change, affine, crs, 'successive signed gamma-0 delta dB')
        cog(directory / interval['score_raster'], score, affine, crs, 'centered median/MAD score; uncalibrated unless stated')
        cog(directory / interval['mask_raster'], np.where(good, labels > 0, 255).astype(np.uint8),
            affine, crs, '1 exploratory retained candidate; 0 background; 255 invalid', 255, True)
        overlay(directory / interval['overlay'], labels, change)
        write_json(directory / f'{pair_id}_regions.geojson', vectorize(labels, affine, crs, regions))
        print(f"{pair_id}: {interval['candidate_area_km2']:.4f} km²; {len(regions)} exploratory regions", flush=True)
    raw_strict, available, count = persistence(raw_masks, valid)
    retained_strict, _, _ = persistence(masks, valid)
    cog(directory / 'persistence.tif', raw_strict, affine, crs, 'raw score transition frequency on fully observed pixels')
    cog(directory / 'persistence_available.tif', available, affine, crs, 'raw transition frequency over available intervals')
    cog(directory / 'candidate_persistence.tif', retained_strict, affine, crs, 'retained candidate transition frequency on fully observed pixels')
    cog(directory / 'valid_interval_count.tif', count, affine, crs, 'number of finite observed intervals', 65535, True)
    labels = fixed_zones(masks)
    series_identity = {k: anchor[k] for k in ('track', 'frame', 'frequency', 'covariance_term',
                                             'product_version', 'range_bandwidth_hz', 'center_frequency_hz')}
    series_identity.update(case_id=config['case_id'], affine=list(affine)[:6], shape=list(shape))
    series_key = json.dumps(series_identity, sort_keys=True)
    zones, rows, recovery = zone_metrics(labels, arrays, masks, valid, observations,
                                         pixel_area, series_key, config['minimum_zone_common_fraction'], epsilon)
    positions = {r['id']: r for r in region_statistics(labels, arrays[-1] - arrays[0], affine, crs)}
    for zone in zones:
        for field in ('centroid_wgs84', 'bbox_projected'):
            zone[field] = positions[zone['id']][field]
    cog(directory / 'zone_labels.tif', labels, affine, crs, 'fixed zone ID; 0 outside tracked candidates', 0, True)
    cog(directory / 'recovery.tif', recovery, affine, crs, 'zone-level latest return-toward-baseline fraction; nodata if unassessable')
    geo = vectorize(labels, affine, crs, zones)
    write_json(directory / 'zones.geojson', geo)
    write_json(directory / 'zone_timeseries.json', rows)
    write_json(directory / 'zones.json', zones)
    parquet_rows(directory / 'zone_timeseries.parquet', rows)
    display = display_regions(labels)
    zone_by_number = {z['id']: z for z in zones}
    for item in display:
        item['zone_id'] = zone_by_number[item['id']]['zone_id']
    write_json(directory / 'zones_display.json', display)
    preview(directory / 'persistence.png', retained_strict, [0, 1])
    preview(directory / 'recovery.png', recovery, [0, 1])
    timeline = {'case_id': config['case_id'], 'event_reference_date': config['event_reference_date'],
                'observations': observations, 'intervals': intervals, 'zones': zones,
                'canonical_grid': {'crs': crs, 'affine': list(affine)[:6], 'shape': list(shape),
                                   'pixel_area_km2': pixel_area},
                'physical_quantity': 'real diagonal HHHH gamma-0 radar power, 10 log10(power), dB',
                'display_limits_db': limits, 'calibration': calibration,
                'cleanup': {'min_region_pixels': params['min_region_pixels'],
                            'opening_iterations': params['opening_iterations'], 'connectivity': 4},
                'minimum_zone_common_fraction': config['minimum_zone_common_fraction'],
                'series_key': series_key,
                'epsilon': epsilon, 'source_code_sha256': code_hash(),
                'software': {'python': sys.version.split()[0], 'gdal': rasterio.__gdal_version__,
                             **{name: importlib.metadata.version(name) for name in
                                ('numpy', 'scipy', 'h5py', 'rasterio', 'pyproj', 'shapely', 'pyarrow')}},
                'selected_observation_count': len(observations), 'audited_file_count': audit['file_count'],
                'new_folder_file_count': sum(r['source_file'].startswith('database for imp2/') for r in audit['records']),
                'persistence_definition': 'fraction of successive intervals exceeding score cutoff; strict map requires all intervals valid',
                'recovery_definition': '1 - abs(mean zone delta from first observation)/abs(observed peak), clamped; reported only at/after peak on fixed common pixels',
                'status_rules': {'returned_toward_baseline': .8, 'returning_toward_baseline': .2,
                                 'interpretation': 'descriptive bands; not independently validated recovery classes'},
                'registration_validation': 'canonical grid equality and source coordinate checks; independent subpixel registration not established',
                'limitations': ['Radar causes remain UNVERIFIED; NISAR is PROVISIONAL.',
                                'No validated score cutoff is available unless a calibration file is supplied.',
                                'Repeat transitions are not proof of a persistent physical disturbance.',
                                'Three samples bracket behavior but cannot identify an exact onset date or establish long-term recovery.',
                                'Fixed union zones merge touching components and do not establish moving-object lineage.',
                                'Signed zone means may cancel changes of opposite sign; mean absolute changes are also exported.',
                                'The August 26 date is a reference marker, not an attribution of radar change to that event.']}
    write_json(directory / 'observations.json', {'case_id': config['case_id'], 'observations': observations,
                                               'canonical_grid': timeline['canonical_grid']})
    write_json(directory / 'timeline.json', timeline)
    public = Path('web/public/cases') / config['case_id'] / 'timeseries'
    public.mkdir(parents=True, exist_ok=True)
    for path in directory.iterdir():
        if path.suffix in {'.json', '.geojson', '.png', '.webp', '.parquet'}:
            shutil.copyfile(path, public / path.name)
    print(f"Time series exported: {len(observations)} observations, {len(intervals)} intervals, {len(zones)} zones", flush=True)
    return timeline


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='config.timeseries.json')
    args = parser.parse_args()
    run(args.config)
