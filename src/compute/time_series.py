"""Descriptive time-series metrics; repeated transitions are distinct from disturbance persistence."""
import hashlib

import numpy as np
from scipy import ndimage

from src.compute.regions import cleaned_labels


def robust_score(change, epsilon=1e-6):
    if not np.isfinite(epsilon) or epsilon <= 0:
        raise ValueError('epsilon must be finite and positive')
    change = np.asarray(change, dtype=np.float32)
    valid = np.isfinite(change)
    if not valid.any():
        raise ValueError('No finite pixels for score normalization')
    center = float(np.median(change[valid]))
    mad = float(np.median(np.abs(change[valid] - center)))
    scale = 1.4826 * mad
    score = (change - center) / (scale + epsilon)
    return score, {'center_db': center, 'mad_db': mad, 'robust_spread_db': scale,
                   'epsilon': epsilon, 'degenerate_spread': scale <= epsilon}


def interval_candidates(change, tau, min_pixels, opening_iterations, epsilon=1e-6):
    if not np.isfinite(tau) or tau <= 0:
        raise ValueError('score threshold must be finite and positive')
    score, normalization = robust_score(change, epsilon)
    raw = (np.abs(score) > tau) & np.isfinite(score)
    if normalization['degenerate_spread']:
        raw[:] = False
    labels = cleaned_labels(raw, np.isfinite(score), min_pixels, opening_iterations)
    return score, raw, labels, normalization


def persistence(masks, valid):
    """The n-1 denominator applies only to pixels observed in every interval."""
    masks = np.asarray(masks, dtype=bool)
    valid = np.asarray(valid, dtype=bool)
    if masks.shape != valid.shape or masks.ndim != 3 or masks.shape[0] < 1:
        raise ValueError('Expected matching interval × row × column arrays')
    count = np.sum(valid, axis=0).astype(np.uint16)
    detections = np.sum(masks & valid, axis=0)
    strict = np.full(count.shape, np.nan, dtype=np.float32)
    full = count == masks.shape[0]
    strict[full] = detections[full] / masks.shape[0]
    available = np.full(count.shape, np.nan, dtype=np.float32)
    np.divide(detections, count, out=available, where=count > 0)
    return strict, available, count


def fixed_zones(masks):
    masks = np.asarray(masks, dtype=bool)
    if masks.ndim != 3:
        raise ValueError('Expected interval masks')
    return ndimage.label(np.any(masks, axis=0), ndimage.generate_binary_structure(2, 1))[0].astype(np.int32)


def recovery_curve(magnitudes, epsilon=1e-6):
    """No recovery value before the observed peak, or for missing/zero disturbance."""
    finite = [(i, abs(float(value))) for i, value in enumerate(magnitudes)
              if value is not None and np.isfinite(value)]
    if not finite:
        return None, [None] * len(magnitudes)
    peak_index, peak = max(finite, key=lambda item: item[1])
    if peak <= epsilon:
        return None, [None] * len(magnitudes)
    curve = []
    for i, value in enumerate(magnitudes):
        if i < peak_index or value is None or not np.isfinite(value):
            curve.append(None)
        else:
            curve.append(float(np.clip(1 - abs(value) / (peak + epsilon), 0, 1)))
    # The peak is the reference, so its recovery is exactly zero.
    curve[peak_index] = 0.0
    return peak_index, curve


def zone_metrics(labels, arrays, interval_masks, interval_valid, observations,
                 pixel_area, series_key, minimum_common_fraction=.9, epsilon=1e-6):
    arrays = np.asarray(arrays)
    masks = np.asarray(interval_masks, dtype=bool)
    valid = np.asarray(interval_valid, dtype=bool)
    if (arrays.ndim != 3 or len(arrays) != len(observations) or
            masks.shape != valid.shape or masks.shape[0] != len(arrays) - 1 or
            labels.shape != arrays.shape[1:] or masks.shape[1:] != labels.shape):
        raise ValueError('Zone inputs do not share observation/interval/grid dimensions')
    common = np.all(np.isfinite(arrays), axis=0)
    zones = []
    rows = []
    recovery_map = np.full(labels.shape, np.nan, np.float32)
    for number, slices in enumerate(ndimage.find_objects(labels), 1):
        if slices is None:
            continue
        footprint = labels[slices] == number
        support = footprint & common[slices]
        count = int(footprint.sum())
        fraction = float(support.sum() / count)
        usable = fraction >= minimum_common_fraction
        local = arrays[(slice(None),) + slices]
        magnitudes = [float(np.mean((image - local[0])[support])) if usable else None for image in local]
        peak_index, recoveries = recovery_curve(magnitudes, epsilon)
        detections = [int(np.count_nonzero(masks[i][slices] & footprint)) for i in range(len(masks))]
        interval_coverage = [float(np.mean(valid[i][slices][footprint])) for i in range(len(masks))]
        observed = [coverage >= minimum_common_fraction for coverage in interval_coverage]
        active = [i for i, pixels in enumerate(detections) if pixels > 0 and observed[i]]
        digest = hashlib.sha256(series_key.encode() + str(slices).encode() + footprint.tobytes()).hexdigest()[:12]
        zone_id = 'NP-Z' + digest
        latest_recovery = recoveries[-1]
        if not usable or latest_recovery is None:
            status = 'INSUFFICIENT_DATA'
        elif peak_index == len(observations) - 1:
            status = 'AT_OBSERVED_PEAK'
        elif latest_recovery >= .8:
            status = 'RETURNED_TOWARD_BASELINE'
        elif latest_recovery >= .2:
            status = 'RETURNING_TOWARD_BASELINE'
        else:
            status = 'REMAINS_NEAR_OBSERVED_PEAK'
        record = {'id': number, 'zone_id': zone_id, 'pixel_count': count,
                  'footprint_area_km2': count * pixel_area, 'common_valid_fraction': fraction,
                  'first_seen': observations[active[0] + 1]['timestamp'] if active else None,
                  'last_seen': observations[active[-1] + 1]['timestamp'] if active else None,
                  'onset_bracket': [observations[active[0]]['timestamp'], observations[active[0] + 1]['timestamp']] if active else None,
                  'peak_area_km2': max(detections, default=0) * pixel_area,
                  'peak_change_db': magnitudes[peak_index] if peak_index is not None else None,
                  'peak_observation_id': observations[peak_index]['observation_id'] if peak_index is not None else None,
                  'persistence': len(active) / sum(observed) if any(observed) else None,
                  'observed_intervals': sum(observed), 'detected_intervals': len(active),
                  'latest_recovery': latest_recovery, 'status': status,
                  'validation_status': 'UNVERIFIED', 'status_type': 'descriptive radar behavior',
                  'tracking_method': 'fixed connected union of successive retained masks; touching/splitting components share one zone'}
        zones.append(record)
        for i, obs in enumerate(observations):
            values = (local[i] - local[0])[support] if usable else np.array([])
            row = {'zone_id': zone_id, 'observation_id': obs['observation_id'], 'timestamp': obs['timestamp'],
                   'area_km2': detections[i - 1] * pixel_area if i else None,
                   'zone_footprint_area_km2': count * pixel_area,
                   'common_valid_fraction': fraction,
                   'mean_delta_from_baseline_db': magnitudes[i],
                   'median_delta_from_baseline_db': float(np.median(values)) if values.size else None,
                   'mean_absolute_delta_from_baseline_db': float(np.mean(np.abs(values))) if values.size else None,
                   'recovery': recoveries[i], 'validation_status': 'UNVERIFIED'}
            rows.append(row)
        if latest_recovery is not None and usable:
            target = recovery_map[slices]
            target[support] = latest_recovery
    return zones, rows, recovery_map
