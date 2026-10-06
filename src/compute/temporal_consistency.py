"""Describe repeat-interval behavior on the unchanged 24-day region pixels."""
from collections import Counter
import csv
import json
from pathlib import Path

import numpy as np
import rasterio

from src.export.artifacts import write_json

# Descriptive rules fixed before examining region-level temporal results.
MIN_VALID_FRACTION = 0.90
MATERIAL_FRACTION = 0.20
MATERIAL_FLOOR_DB = 0.50
DOMINANT_SHARE = 0.70
ACCUMULATION_TOLERANCE_FRACTION = 0.30
ACCUMULATION_TOLERANCE_FLOOR_DB = 1.00


def signed(value):
    return 'increase' if value > 0 else 'decrease' if value < 0 else 'neutral'


def classify(final_median, early_median, late_median, valid_fraction=1.0):
    """Return a descriptive class, never a statistical confidence label."""
    values=(final_median,early_median,late_median,valid_fraction)
    if not all(np.isfinite(values)) or valid_fraction < MIN_VALID_FRACTION or final_median == 0:
        return 'UNSTABLE'
    material=max(MATERIAL_FLOOR_DB,MATERIAL_FRACTION*abs(final_median))
    early_sign=np.sign(early_median);late_sign=np.sign(late_median);final_sign=np.sign(final_median)
    if early_sign != late_sign and min(abs(early_median),abs(late_median)) >= material:
        return 'MIXED_SIGN'
    total=abs(early_median)+abs(late_median)
    if total == 0:
        return 'UNSTABLE'
    if early_sign == final_sign and abs(early_median)/total >= DOMINANT_SHARE and abs(late_median) < material:
        return 'EARLY_DOMINANT'
    if late_sign == final_sign and abs(late_median)/total >= DOMINANT_SHARE and abs(early_median) < material:
        return 'LATE_DOMINANT'
    tolerance=max(ACCUMULATION_TOLERANCE_FLOOR_DB,
                  ACCUMULATION_TOLERANCE_FRACTION*abs(final_median))
    if (early_sign == late_sign == final_sign and
        min(abs(early_median),abs(late_median)) >= material and
        abs(early_median+late_median-final_median) <= tolerance):
        return 'CUMULATIVE_CONSISTENT'
    return 'UNSTABLE'


def interval_statistics(values, cutoff):
    return {'median_delta_db':float(np.median(values)),
            'mean_delta_db':float(np.mean(values)),
            'positive_fraction':float(np.mean(values>0)),
            'negative_fraction':float(np.mean(values<0)),
            'abs_change_median_db':float(np.median(np.abs(values))),
            'fraction_above_nominal_cutoff':float(np.mean(np.abs(values)>=cutoff)),
            'nominal_cutoff_db':float(cutoff)}


def augment_geojson(original, records):
    """Copy properties onto exact original geometry, without resampling."""
    by_id={r['region_id']:r for r in records}
    result={'type':'FeatureCollection','features':[]}
    for feature in original['features']:
        item=json.loads(json.dumps(feature))
        region=by_id[item['properties']['id']]
        item['properties']['temporal_class']=region['temporal_class']
        item['properties']['temporal_valid_fraction']=region['valid_fraction']
        result['features'].append(item)
    if len(result['features'])!=len(records):
        raise ValueError('Original region geometry count differs from temporal records')
    return result


def compute(case_dir):
    case_dir=Path(case_dir)
    paths={name:case_dir/name for name in ('t1_t2','t1_t3','t2_t3')}
    evidence={name:json.loads((path/'evidence.json').read_text()) for name,path in paths.items()}
    images={};grids={}
    for name,path in paths.items():
        with rasterio.open(path/'change_raw.tif') as ds:
            images[name]=ds.read(1)
            grids[name]=(ds.transform,ds.crs,ds.width,ds.height)
    if len({str(grid) for grid in grids.values()})!=1:
        raise ValueError('Temporal rasters do not share an exact grid')
    with rasterio.open(paths['t1_t3']/'region_labels.tif') as ds:
        labels=ds.read(1)
        if (ds.transform,ds.crs,ds.width,ds.height)!=grids['t1_t3']:
            raise ValueError('Reference region labels are not aligned')
    valid=np.isfinite(images['t1_t2'])&np.isfinite(images['t1_t3'])&np.isfinite(images['t2_t3'])
    # These differences are algebraically additive on common valid pixels.
    identity_error=float(np.max(np.abs((images['t1_t2'][valid].astype(np.float64)+
                         images['t2_t3'][valid])-images['t1_t3'][valid])))
    if identity_error>1e-4:
        raise ValueError(f'Signed change rasters are not additive: {identity_error} dB')
    records=[]
    for region in evidence['t1_t3']['regions']:
        region_id=region['id'];inside=labels==region_id
        count=int(np.count_nonzero(inside));good=inside&valid;good_count=int(np.count_nonzero(good))
        if count!=region['pixel_count']:
            raise ValueError(f'Reference pixel count changed for region {region_id}')
        fraction=good_count/count if count else 0
        metrics={}
        for pair in ('t1_t2','t2_t3','t1_t3'):
            values=images[pair][good]
            metrics[pair]=interval_statistics(values,evidence[pair]['analysis']['threshold_db']) if good_count else None
        category=classify(metrics['t1_t3']['median_delta_db'],metrics['t1_t2']['median_delta_db'],
                          metrics['t2_t3']['median_delta_db'],fraction) if good_count else 'UNSTABLE'
        records.append({'region_id':region_id,'area_km2':region['area_km2'],'pixel_count':count,
           'valid_pixel_count':good_count,'valid_fraction':fraction,
           'centroid_wgs84':region['centroid_wgs84'],'bbox_projected':region['bbox_projected'],
           't1_t2':metrics['t1_t2'],'t2_t3':metrics['t2_t3'],
           't1_t3':{'median_delta_db':metrics['t1_t3']['median_delta_db'],
                    'mean_delta_db':metrics['t1_t3']['mean_delta_db'],
                    'sign':signed(metrics['t1_t3']['median_delta_db'])} if good_count else None,
           'temporal_class':category,'classification_type':'descriptive, not statistical',
           'validation_status':'UNVERIFIED'})
    dataset=evidence['t1_t3']['dataset']
    report={'case_id':evidence['t1_t3']['case_id'],'reference_pair':'t1_t3',
      'reference_geometry':'unchanged t1_t3 nominal retained-region native pixels',
      'acquisition_dates_utc':[source['acquisition_start']+'Z' for source in dataset['sources']],
      'source_granule_ids':dataset['granule_ids'],
      'subintervals':{name:{'source_files':evidence[name]['dataset']['source_files'],
                             'source_granule_ids':evidence[name]['dataset']['granule_ids'],
                             'nominal_cutoff_db':evidence[name]['analysis']['threshold_db']}
                       for name in ('t1_t2','t2_t3')},
      'rules':{'minimum_valid_fraction':MIN_VALID_FRACTION,'material_fraction_of_final_median':MATERIAL_FRACTION,
               'material_floor_db':MATERIAL_FLOOR_DB,'dominant_share':DOMINANT_SHARE,
               'accumulation_tolerance_fraction':ACCUMULATION_TOLERANCE_FRACTION,
               'accumulation_tolerance_floor_db':ACCUMULATION_TOLERANCE_FLOOR_DB},
      'additivity_max_abs_error_db':identity_error,
      'class_counts':dict(Counter(r['temporal_class'] for r in records)),
      'regions':records,'provisional':True,'interpretation':'descriptive temporal radar behavior; causes UNVERIFIED'}
    write_json(case_dir/'temporal_consistency.json',report)
    original=json.loads((paths['t1_t3']/'change_regions.geojson').read_text())
    write_json(case_dir/'temporal_consistency.geojson',augment_geojson(original,records))
    columns=['region_id','area_km2','pixel_count','valid_pixel_count','valid_fraction',
      'centroid_lon','centroid_lat','temporal_class','validation_status']
    for pair in ('t1_t2','t2_t3'):
        columns.extend(f'{pair}_{field}' for field in ('median_delta_db','mean_delta_db','positive_fraction',
          'negative_fraction','abs_change_median_db','fraction_above_nominal_cutoff'))
    columns.extend(['t1_t3_median_delta_db','t1_t3_mean_delta_db','t1_t3_sign'])
    with (case_dir/'temporal_consistency.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns);writer.writeheader()
        for record in records:
            row={key:record[key] for key in columns if key in record}
            row['centroid_lon'],row['centroid_lat']=record['centroid_wgs84']
            for pair in ('t1_t2','t2_t3'):
                if record[pair]:
                    for field in ('median_delta_db','mean_delta_db','positive_fraction',
                      'negative_fraction','abs_change_median_db','fraction_above_nominal_cutoff'):
                        row[f'{pair}_{field}']=record[pair][field]
            if record['t1_t3']:
                for field in ('median_delta_db','mean_delta_db','sign'):
                    row[f't1_t3_{field}']=record['t1_t3'][field]
            writer.writerow(row)
    return report


if __name__=='__main__':
    result=compute('data/derived/nepal_case_01')
    print(f"Temporal analysis: {len(result['regions'])} reference regions; {result['class_counts']}")
