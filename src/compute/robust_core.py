"""Export native-grid change that survives the nominal and +10% cutoff rules."""
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage

from src.compute.area import mask_area_km2
from src.compute.regions import cleaned_labels
from src.compute.threshold import candidate_mask
from src.export.artifacts import write_json, raster, vectorize, display_regions, overlay


def core_labels(nominal_labels,change,strict_threshold,min_pixels,opening_iterations):
    if nominal_labels.shape!=change.shape:
        raise ValueError('Nominal labels and change raster differ in shape')
    valid=np.isfinite(change)
    strict=cleaned_labels(candidate_mask(change,strict_threshold),valid,
                          min_pixels,opening_iterations)>0
    result=np.where(valid&strict&(nominal_labels>0),nominal_labels,0)
    return result.astype(np.int32)


def compute_pair(pair_dir):
    pair_dir=Path(pair_dir)
    evidence=json.loads((pair_dir/'evidence.json').read_text())
    with rasterio.open(pair_dir/'change_raw.tif') as ds:
        change=ds.read(1);affine=ds.transform;crs=ds.crs
    with rasterio.open(pair_dir/'region_labels.tif') as ds:
        nominal=ds.read(1)
        if (ds.transform,ds.crs)!=(affine,crs):
            raise ValueError('Nominal labels and change grid differ')
    fraction=evidence['analysis']['sensitivity_fraction']
    nominal_threshold=evidence['analysis']['threshold_db']
    strict_threshold=nominal_threshold*(1+fraction)
    cleanup=evidence['analysis']['cleanup']
    core=core_labels(nominal,change,strict_threshold,
         cleanup['min_region_pixels'],cleanup['opening_iterations'])
    mask=np.where(np.isfinite(change),(core>0).astype(np.uint8),255).astype(np.uint8)
    raster(pair_dir/'robust_core_mask.tif',mask,affine,crs,255,'1 robust candidate core; 0 background; 255 invalid')
    robust_regions=[]
    for nominal_region in evidence['regions']:
        region_id=nominal_region['id'];selection=core==region_id
        pixels=int(np.count_nonzero(selection))
        if not pixels:continue
        values=change[selection]
        robust_area=mask_area_km2(selection,affine,crs)
        nominal_area=nominal_region['area_km2']
        robust_regions.append({'id':region_id,'region_id':region_id,
           'robust_area_km2':robust_area,'nominal_area_km2':nominal_area,
           'robust_fraction':robust_area/nominal_area,'pixel_count':pixels,
           'median_delta_db':float(np.median(values)),
           'mean_delta_db':float(np.mean(values)),
           'sign':'increase' if np.median(values)>0 else 'decrease' if np.median(values)<0 else 'neutral',
           'validation_status':'UNVERIFIED','interpretation':'robust candidate core'})
    area=mask_area_km2(core>0,affine,crs)
    connected_count=int(ndimage.label(core>0,ndimage.generate_binary_structure(2,1))[1])
    result={'pair_id':evidence['pair_id'],'provisional':True,
      'definition':'nominal retained pixels surviving the same cleanup at the +10% stricter cutoff',
      'nominal_threshold_db':nominal_threshold,'strict_threshold_db':strict_threshold,
      'threshold_increase_fraction':fraction,
      'summary':{'robust_area_km2':area,'nominal_area_km2':evidence['summary']['changed_area_km2'],
                 'robust_fraction_of_nominal':area/evidence['summary']['changed_area_km2'] if evidence['summary']['changed_area_km2'] else None,
                 'nominal_region_count_with_core':len(robust_regions),'connected_core_count':connected_count},
      'regions':robust_regions,'source_granule_ids':evidence['dataset']['granule_ids'],
      'validation_status':'UNVERIFIED','note':'Threshold persistence is not statistical confidence.'}
    write_json(pair_dir/'robust_core.json',result)
    write_json(pair_dir/'robust_core_regions.geojson',vectorize(core,affine,crs,robust_regions))
    write_json(pair_dir/'robust_core_display.json',display_regions(core))
    overlay(pair_dir/'robust_core_overlay.png',core,change)
    return result


if __name__=='__main__':
    for name in ('t1_t2','t1_t3','t2_t3'):
        result=compute_pair(Path('data/derived/nepal_case_01')/name)
        print(name,result['summary'])
