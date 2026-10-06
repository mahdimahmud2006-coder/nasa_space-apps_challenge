"""Fail closed unless audited grids coincide; crop via a shared source window."""
import numpy as np
from src.ingest.metadata import compatibility


def verify_pair(before, after):
    check=compatibility(before,after)
    if not check['accepted']:
        raise ValueError('; '.join(check['reasons']))
    return check


def common_valid(before,after):
    if before.shape!=after.shape:
        raise ValueError('Unaligned raster shapes')
    return np.isfinite(before)&np.isfinite(after)
