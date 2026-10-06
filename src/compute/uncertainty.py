import numpy as np
from .threshold import candidate_mask
from .regions import cleaned_labels
from .area import mask_area_km2


def threshold_sensitivity(change,threshold,transform,crs,min_pixels,opening_iterations,fraction=.1):
    if not 0<fraction<1:
        raise ValueError('Sensitivity fraction must be between zero and one')
    output={}
    for label,factor in [('lower_threshold',1-fraction),('nominal',1),('higher_threshold',1+fraction)]:
        value=threshold*factor
        labels=cleaned_labels(candidate_mask(change,value),np.isfinite(change),min_pixels,opening_iterations)
        output[label]={'threshold_db':value,'area_km2':mask_area_km2(labels>0,transform,crs),
                       'region_count':int(labels.max())}
    return output
