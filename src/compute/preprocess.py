"""Optional small median filter with strict protection of nodata boundaries."""
import numpy as np
from scipy import ndimage


def median_db(array,size=3):
    if size<1 or size%2==0 or size>7:
        raise ValueError('Median filter size must be odd, between 1 and 7')
    if size==1:
        return array.copy()
    # No output is valid unless every contributing source pixel was valid.
    valid=ndimage.binary_erosion(np.isfinite(array),structure=np.ones((size,size)),border_value=0)
    result=ndimage.median_filter(np.nan_to_num(array,nan=0,posinf=0,neginf=0),size=size,mode='constant')
    result[~valid]=np.nan
    return result
