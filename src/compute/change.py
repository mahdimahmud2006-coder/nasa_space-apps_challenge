"""Signed change in gamma-0 power expressed in decibels."""
import numpy as np
from .align import common_valid


def delta_db(before,after):
    valid=common_valid(before,after)
    result=np.full(before.shape,np.nan,dtype=np.float32)
    result[valid]=after[valid]-before[valid]
    return result


def distribution(change):
    data=change[np.isfinite(change)]
    if not data.size:
        raise ValueError('No common valid pixels')
    median=float(np.median(data))
    extent=max(float(np.abs(data).max()),1e-6)
    counts,edges=np.histogram(data,bins=80,range=(-extent,extent))
    return {'count':int(data.size),'min':float(data.min()),'max':float(data.max()),
            'mean':float(data.mean()),'median':median,'std':float(data.std()),
            'mad':float(np.median(np.abs(data-median))),
            'percentiles':{str(p):float(np.percentile(data,p)) for p in [1,5,25,50,75,95,99]},
            'histogram':{'counts':counts.tolist(),'edges_db':edges.tolist()}}
