import copy
import json
from pathlib import Path

from affine import Affine
import h5py
import numpy as np
import pytest
import rasterio

from src.compute.time_series import robust_score, interval_candidates, persistence, fixed_zones, recovery_curve, zone_metrics
from src.compute.timeseries_pipeline import canonical_observation, cog, parquet_rows, threshold_setting
from src.ingest.inspect_h5 import inspect
from src.ingest.timeseries import PHYSICAL_KEYS, incompatibilities, select_series, discover


def test_score_is_centered_and_uses_mad():
    values = np.array([[1., 2., 3., 4., 5., np.nan]])
    z, stats = robust_score(values)
    np.testing.assert_allclose(z[0, :5], (values[0, :5] - 3) / (1.4826 + 1e-6))
    assert stats['center_db'] == 3
    assert stats['mad_db'] == 1
    assert np.isnan(z[0, -1])


def test_uniform_shift_is_not_a_centered_spatial_anomaly():
    z, raw, labels, stats = interval_candidates(np.full((8, 8), 4.), 3, 1, 0)
    assert stats['degenerate_spread']
    assert not raw.any() and not labels.any()
    assert (z == 0).all()


def test_score_requires_finite_pixels():
    with pytest.raises(ValueError, match='finite pixels'):
        robust_score(np.full((3, 3), np.nan))


@pytest.mark.parametrize('tau', [0, -1, float('nan')])
def test_bad_score_threshold_rejected(tau):
    with pytest.raises(ValueError):
        interval_candidates(np.arange(9).reshape(3, 3), tau, 1, 0)


def test_persistence_missing_interval_is_not_stability():
    masks = np.array([[[1, 1, 1]], [[0, 1, 1]], [[1, 0, 0]]], bool)
    valid = np.array([[[1, 1, 0]], [[1, 0, 0]], [[1, 1, 0]]], bool)
    strict, available, count = persistence(masks, valid)
    assert strict[0, 0] == pytest.approx(2 / 3)
    assert np.isnan(strict[0, 1:]).all()
    assert available[0, 1] == pytest.approx(.5)
    assert np.isnan(available[0, 2])
    assert count.tolist() == [[3, 2, 0]]


def test_recovery_is_only_at_or_after_observed_peak():
    peak, recovery = recovery_curve([0., -5., -1.])
    assert peak == 1 and recovery[0] is None and recovery[1] == 0
    assert recovery[2] == pytest.approx(.8, abs=1e-6)


def test_recovery_zero_or_missing_not_fabricated():
    assert recovery_curve([0, 0, None]) == (None, [None, None, None])
    peak, curve = recovery_curve([0, 4, None])
    assert peak == 1 and curve[-1] is None


def test_fixed_union_zone_tracks_touching_components():
    masks = np.zeros((2, 8, 8), bool)
    masks[0, 1:3, 1:3] = True
    masks[1, 2:4, 2:4] = True
    labels = fixed_zones(masks)
    assert labels.max() == 1
    assert np.count_nonzero(labels) == 7


def zone_fixture():
    observations = [{'observation_id': f't{i}', 'timestamp': f'2026-08-{1 + i * 12:02}T00:00:00Z'} for i in range(3)]
    images = np.stack([np.zeros((4, 4)), np.full((4, 4), 5.), np.ones((4, 4))])
    masks = np.zeros((2, 4, 4), bool)
    masks[0, 1:3, 1:3] = True
    labels = fixed_zones(masks)
    return observations, images, masks, labels


def test_zone_baseline_support_onset_area_and_recovery():
    observations, images, masks, labels = zone_fixture()
    valid = np.ones_like(masks)
    zones, rows, recovery = zone_metrics(labels, images, masks, valid, observations, .0001, 'series')
    zone = zones[0]
    assert zone['footprint_area_km2'] == pytest.approx(.0004)
    assert zone['persistence'] == .5
    assert zone['onset_bracket'] == [observations[0]['timestamp'], observations[1]['timestamp']]
    assert zone['peak_change_db'] == 5
    assert zone['latest_recovery'] == pytest.approx(.8, abs=1e-6)
    assert rows[0]['recovery'] is None
    assert rows[0]['area_km2'] is None
    assert np.isfinite(recovery).sum() == 4
    repeated = zone_metrics(labels, images, masks, valid, observations, .0001, 'series')[0]
    assert zone['zone_id'] == repeated[0]['zone_id']


def test_missing_zone_observation_is_not_recovery():
    observations, images, masks, labels = zone_fixture()
    images[-1, 1:3, 1:3] = np.nan
    valid = np.isfinite(images[1:]) & np.isfinite(images[:-1])
    zones, rows, recovery = zone_metrics(labels, images, masks, valid, observations, .0001, 'series')
    assert zones[0]['status'] == 'INSUFFICIENT_DATA'
    assert zones[0]['latest_recovery'] is None
    assert all(row['mean_delta_from_baseline_db'] is None for row in rows)
    assert np.isnan(recovery).all()


def test_hdf5_named_datatype_is_audited(tmp_path):
    path = tmp_path / 'quad.h5'
    with h5py.File(path, 'w') as f:
        f['committed_complex'] = np.dtype('complex64')
        f.create_dataset('power', data=np.ones((3, 3)))
    result = inspect(path)
    assert len(result['datasets']) == 1
    assert result['named_datatypes'][0]['path'] == '/committed_complex'


def metadata_record(name='anchor', day=1):
    result = {key: 'same' for key in PHYSICAL_KEYS}
    result.update(product='GCOV', level='L2', source_file=name,
                  acquisition_start=f'2026-08-{day:02}T00:00:00Z')
    return result


@pytest.mark.parametrize('key', ['track', 'frame', 'product_version', 'range_bandwidth_hz',
                                 'center_frequency_hz', 'source_polarizations', 'dithered'])
def test_different_physical_acquisition_not_mixed(key):
    anchor = metadata_record()
    candidate = copy.deepcopy(anchor)
    candidate[key] = 'different'
    assert any(key in reason for reason in incompatibilities(anchor, candidate))


def test_select_series_orders_dates_and_excludes_duplicates():
    data = [metadata_record('third', 25), metadata_record('anchor', 1),
            metadata_record('second', 13), metadata_record('zz_duplicate', 13)]
    selected = select_series(data, 'anchor')
    assert [r['source_file'] for r in selected] == ['anchor', 'second', 'third']
    assert data[-1]['selected'] is False


def test_only_two_compatible_dates_not_complete_series():
    with pytest.raises(ValueError, match='At least three'):
        select_series([metadata_record('anchor', 1), metadata_record('second', 13)], 'anchor')


def test_cog_preserves_native_values_and_grid(tmp_path):
    image = np.arange(512 * 512, dtype=np.float32).reshape(512, 512)
    image[0, 0] = np.nan
    path = tmp_path / 'test.tif'
    affine = Affine(10, 0, 300000, 0, -10, 3100000)
    cog(path, image, affine, 'EPSG:32645', 'test measurement')
    with rasterio.open(path) as ds:
        assert ds.tags(ns='IMAGE_STRUCTURE')['LAYOUT'] == 'COG'
        assert ds.transform == affine and ds.crs.to_epsg() == 32645
        assert ds.overviews(1)
        np.testing.assert_equal(ds.read(1), image)


def test_reprojection_excludes_invalid_contributors(tmp_path):
    path = tmp_path / 'source.h5'
    with h5py.File(path, 'w') as f:
        g = f.create_group('grid')
        g.create_dataset('HHHH', data=np.ones((10, 10), np.float32))
        mask = np.ones((10, 10), np.uint8); mask[4, 4] = 0
        g.create_dataset('mask', data=mask)
        g.create_dataset('numberOfLooks', data=np.ones((10, 10), np.float32))
        g.create_dataset('xCoordinates', data=np.arange(5, 100, 10))
        g.create_dataset('yCoordinates', data=np.arange(95, 0, -10))
        g.create_dataset('projection', data=32645)
    source = {'source_file': str(path), 'spacing': [10, -10], 'origin_center': [5, 95],
              'shape': [10, 10], 'crs': 'EPSG:32645', 'grid_path': '/grid',
              'layer_path': '/grid/HHHH', 'covariance_term': 'HHHH'}
    image, quality = canonical_observation(source, Affine(10, 0, 25, 0, -10, 75), 'EPSG:32645', (5, 5), 1)
    assert 'reprojection' in quality['alignment']
    assert np.isnan(image).sum() >= 4
    assert np.isfinite(image).any()


def test_empty_parquet_preserves_explicit_schema(tmp_path):
    import pyarrow.parquet as pq
    path = tmp_path / 'zones.parquet'
    parquet_rows(path, [])
    table = pq.read_table(path)
    assert table.num_rows == 0
    assert 'mean_delta_from_baseline_db' in table.column_names


def test_uncalibrated_setting_is_explicit():
    tau, record = threshold_setting({}, {'change': {'threshold_value': 3}})
    assert tau == 3 and record['calibration_status'] == 'UNCALIBRATED'
    assert record['validation_source'] is None


def test_calibration_from_different_metric_rejected(tmp_path):
    path = tmp_path / 'calibration.json'
    path.write_text(json.dumps({'calibration_status': 'VALIDATED', 'validation_source': 'field labels',
                                'metric': 'different', 'threshold': 4}))
    with pytest.raises(ValueError, match='score metric'):
        threshold_setting({'threshold_validation_file': str(path)}, {})
