"""Projected grid area using affine determinant and verified CRS units."""
import numpy as np
from pyproj import CRS


def pixel_area_km2(transform,crs):
    parsed=CRS.from_user_input(crs)
    if not parsed.is_projected:
        raise ValueError('Geographic CRS needs geodesic area; use a projected grid')
    factors=[axis.unit_conversion_factor for axis in parsed.axis_info[:2]]
    if len(factors)!=2 or any(f is None for f in factors):
        raise ValueError('Cannot determine CRS linear units')
    area=abs(transform.a*transform.e-transform.b*transform.d)*factors[0]*factors[1]/1e6
    if area<=0:
        raise ValueError('Invalid pixel geometry')
    return area


def mask_area_km2(mask,transform,crs):
    return int(np.count_nonzero(mask))*pixel_area_km2(transform,crs)
