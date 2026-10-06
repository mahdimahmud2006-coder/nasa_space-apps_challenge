"""Configurable zero-centered absolute-change threshold."""
import numpy as np


def cutoff(stats,method,value):
    if not np.isfinite(value) or value<=0:
        raise ValueError('Threshold parameter must be finite and positive')
    if method=='mad':
        spread=1.4826*stats['mad']
        if spread <= 0:
            raise ValueError('MAD is zero; explicitly choose an absolute_db threshold')
        return value*spread
    if method=='absolute_db':
        return float(value)
    raise ValueError('Supported thresholds: mad, absolute_db')


def candidate_mask(change,threshold):
    if not np.isfinite(threshold) or threshold<=0:
        raise ValueError('Threshold must be positive')
    return np.isfinite(change)&(np.abs(change)>=threshold)
