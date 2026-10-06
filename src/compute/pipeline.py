"""Reproduce TerraPulse's audited, local three-observation case."""
import argparse
import hashlib
import importlib.metadata
from itertools import combinations
import json
from pathlib import Path
import shutil
import sys

import numpy as np
from rasterio.warp import transform_geom
from shapely.geometry import box, mapping
from src.ingest.metadata import build_inventory, parse_date
from src.ingest.extract_gcov import analysis_window, extract
from src.compute.align import verify_pair
from src.compute.change import delta_db, distribution
from src.compute.threshold import cutoff, candidate_mask
from src.compute.regions import cleaned_labels, region_statistics
from src.compute.area import mask_area_km2, pixel_area_km2
from src.compute.uncertainty import threshold_sensitivity
from src.compute.preprocess import median_db
from src.export.artifacts import write_json, raster, vectorize, preview, overlay, display_regions

LIMITATIONS=[
 'NISAR L2 GCOV is PROVISIONAL; calibration and quality assurance are ongoing.',
 'Radar backscatter change does not identify its cause. All regions are UNVERIFIED.',
 'Speckle, soil moisture, vegetation, local incidence angle and terrain effects can create change.',
 'Mask and number-of-looks quality gates are applied; independent optical-pixel validation and event attribution are not established.',
 'Areas depend on threshold and connected-region cleanup. Sensitivity is not statistical confidence.',
 'Area is projected grid area in UTM, not ellipsoidal ground area; minor projection distortion is possible.',
 'A fixed small AOI is analyzed; this is not a Nepal-wide disaster inventory.'
]


def code_hash():
    hasher=hashlib.sha256()
    for path in sorted(Path('src').rglob('*.py')):
        hasher.update(str(path).encode()); hasher.update(path.read_bytes())
    return hasher.hexdigest()


def run(config_path):
    config=json.loads(Path(config_path).read_text())
    params=config['change']
    if params['metric']!='delta_db':
        raise ValueError('Only delta_db is implemented')
    if not isinstance(params['min_region_pixels'],int) or not isinstance(params['opening_iterations'],int):
        raise ValueError('Cleanup parameters must be integers')
    inventory=build_inventory('data/derived/audit.json',config['frequency'],config['covariance_term'])
    write_json(Path('data/derived/inventory.json'),inventory)
    by_name={o['filename']:o for o in inventory['observations']}
    selected=[by_name[name] for name in config['source_files']]
    selected.sort(key=lambda o:parse_date(o['acquisition_start']))
    checks=[verify_pair(a,b) for a,b in combinations(selected,2)]
    if len(selected)<2:
        raise ValueError('At least two valid observations are required')
    for source in selected:
        if Path(config['raw_directory'],source['filename']).stat().st_size!=source['size_bytes']:
            raise ValueError('Source changed since audit; rerun inspect')
    output=Path('data/derived')/config['case_id']
    output.mkdir(parents=True,exist_ok=True)
    window,affine=analysis_window(selected[0],config['aoi_center_wgs84'],config['aoi_size_m'])
    crs=selected[0]['crs']
    # The analysis raster transform is the exact snapped pixel boundary.
    aoi_projected=mapping(box(affine.c,affine.f+window.height*affine.e,
                              affine.c+window.width*affine.a,affine.f))
    aoi=transform_geom(crs,4326,aoi_projected,precision=7)
    write_json(output/'aoi.geojson',{'type':'FeatureCollection','features':[
      {'type':'Feature','geometry':aoi,'properties':{'reason':config['aoi_reason']}}]})
    observations=[]; arrays=[]
    for index,source in enumerate(selected):
        print(f"Extracting {source['filename']} at native pixel spacing…",flush=True)
        array,quality=extract(Path(config['raw_directory'])/source['filename'],source,window)
        if quality['valid_pixels']/quality['total_pixels']<.8:
            raise ValueError(f"Insufficient valid AOI coverage: {source['filename']}")
        key=f't{index+1}'
        raster(output/f'{key}_native.tif',array,affine,crs,np.nan,'native gamma-0 backscatter (dB)')
        array=median_db(array,params.get('median_filter_size',1))
        quality['analysis_valid_pixels']=int(np.isfinite(array).sum())
        arrays.append(array)
        raster(output/f'{key}.tif',array,affine,crs,np.nan,'gamma-0 backscatter (dB)')
        observations.append({**source,'id':key,'quality':quality,
          'source_url':'https://doi.org/'+source['doi'],'preview':f'{key}.webp'})
    valid_values=np.concatenate([a[np.isfinite(a)] for a in arrays])
    limits=np.percentile(valid_values,[2,98]).tolist()
    if limits[1]<=limits[0]:
        limits[1]=limits[0]+1
    del valid_values
    for ob,array in zip(observations,arrays):
        preview(output/ob['preview'],array,limits)
    software={'terrapulse':'1.0.0','python':sys.version.split()[0],'source_code_sha256':code_hash(),
              **{p:importlib.metadata.version(p) for p in ['numpy','scipy','h5py','rasterio','pyproj','shapely','pillow']}}
    metadata={'case_id':config['case_id'],'title':config['title'],'provisional':True,'observations':observations,
      'pair_checks':checks,'aoi':{'geometry':aoi,'reason':config['aoi_reason'],'crs':crs,
      'affine':list(affine)[:6],'shape':[int(window.height),int(window.width)],
      'source_window':{'row':int(window.row_off),'col':int(window.col_off),
                       'height':int(window.height),'width':int(window.width)}},
      'display':{'shared_backscatter_limits_db':limits,'preview_max_dimension':1200},'software':software}
    write_json(output/'metadata.json',metadata)
    manifest={'case_id':config['case_id'],'title':config['title'],'status':'PROVISIONAL',
              'observations':observations,'aoi':metadata['aoi'],'pairs':[]}
    for i,j in combinations(range(len(arrays)),2):
        pair_id=f't{i+1}_t{j+1}'
        pair_dir=output/pair_id; pair_dir.mkdir(exist_ok=True)
        change=delta_db(arrays[i],arrays[j]); stats=distribution(change)
        valid=np.isfinite(change)
        if valid.mean()<.8:
            raise ValueError('Insufficient common valid AOI area')
        threshold=cutoff(stats,params['threshold_method'],params['threshold_value'])
        labels=cleaned_labels(candidate_mask(change,threshold),valid,
                              params['min_region_pixels'],params['opening_iterations'])
        regions=region_statistics(labels,change,affine,crs)
        area=mask_area_km2(labels>0,affine,crs)
        sensitivity=threshold_sensitivity(change,threshold,affine,crs,params['min_region_pixels'],
                             params['opening_iterations'],params['sensitivity_fraction'])
        method={'preprocessing':['Windowed native-grid extraction; no resampling or mosaicking',
           'Finite positive power; mask values 1–254; finite positive numberOfLooks',
           '10 * log10(real diagonal gamma-0 power)',
           f"{params.get('median_filter_size',1)} × {params.get('median_filter_size',1)} median per observation; all contributing pixels must be valid",
           'Common finite-pixel mask'],
           'median_filter_size':params.get('median_filter_size',1),
           'metric':'delta_db = after_db - before_db',
           'threshold_rule':'abs(delta_db) >= multiplier * 1.4826 * MAD(delta_db)' if params['threshold_method']=='mad' else 'abs(delta_db) >= configured dB cutoff',
           'threshold_method':params['threshold_method'],'threshold_parameter':params['threshold_value'],
           'threshold_db':threshold,'threshold_center_db':0,'distribution_median_db':stats['median'],
           'cleanup':{'opening_iterations':params['opening_iterations'],'structure':'four-connected cross (3 × 3)',
                      'min_region_pixels':params['min_region_pixels'],'connectivity':4},
           'area_method':'absolute affine determinant × CRS linear-unit factors; projected grid area',
           'pixel_area_km2':pixel_area_km2(affine,crs),
           'ranking':'area descending, then absolute median change descending',
           'validation_status':'UNVERIFIED','sensitivity_fraction':params['sensitivity_fraction'],
           'sensitivity_note':f"±{params['sensitivity_fraction']*100:g}% of nominal cutoff, repeating identical cleanup; not confidence intervals",
           'provisional':True,'software':software,
           'threshold_candidates':[]}
        for multiplier in [2.0,2.5,3.0]:
            candidate_threshold=multiplier*1.4826*stats['mad']
            if candidate_threshold>0:
                candidate_labels=cleaned_labels(candidate_mask(change,candidate_threshold),valid,
                    params['min_region_pixels'],params['opening_iterations'])
                method['threshold_candidates'].append({'mad_multiplier':multiplier,
                  'threshold_db':candidate_threshold,'area_km2':mask_area_km2(candidate_labels>0,affine,crs),
                  'region_count':int(candidate_labels.max())})
        evidence={'case_id':config['case_id'],'pair_id':pair_id,'title':config['title'],
          'dataset':{'mission':'NASA-ISRO NISAR','product':'L2 GCOV PROVISIONAL',
           'collection':'NISAR_L2_GCOV_PROVISIONAL_V1','provisional':True,
           'source_files':[observations[i]['filename'],observations[j]['filename']],
           'granule_ids':[observations[i]['granule_id'],observations[j]['granule_id']],
           'sources':[observations[i],observations[j]],'polarization':config['covariance_term'][:2],
           'covariance_term':config['covariance_term'],'hdf5_path':observations[i]['layer_path'],
           'acquisition_before':observations[i]['acquisition_start']+'Z',
           'acquisition_after':observations[j]['acquisition_start']+'Z'},
          'analysis':method,'summary':{'changed_area_km2':area,'region_count':len(regions),
            'common_valid_area_km2':mask_area_km2(valid,affine,crs),'common_valid_pixels':int(valid.sum()),
            'changed_fraction_of_valid_area':area/mask_area_km2(valid,affine,crs)},
          'distribution':stats,'threshold_sensitivity':sensitivity,'regions':regions,
          'aoi':metadata['aoi'],'limitations':LIMITATIONS,'validation_status':'UNVERIFIED'}
        raster(pair_dir/'change_raw.tif',change,affine,crs,np.nan,'after − before gamma-0 (dB)')
        mask=np.where(valid,(labels>0).astype(np.uint8),255).astype(np.uint8)
        raster(pair_dir/'change_mask.tif',mask,affine,crs,255,'0 unchanged; 1 candidate; 255 invalid')
        raster(pair_dir/'region_labels.tif',np.where(valid,labels,-1).astype(np.int32),affine,crs,-1,'candidate region ID; 0 background; -1 invalid')
        write_json(pair_dir/'change_regions.geojson',vectorize(labels,affine,crs,regions))
        write_json(pair_dir/'regions_display.json',display_regions(labels))
        write_json(pair_dir/'evidence.json',evidence); write_json(pair_dir/'methodology.json',method)
        preview(pair_dir/'change.webp',change,[-threshold*2,threshold*2],'change')
        preview(pair_dir/'change.png',change,[-threshold*2,threshold*2],'change')
        overlay(pair_dir/'overlay.png',labels,change)
        entry={'id':pair_id,'before':observations[i]['id'],'after':observations[j]['id'],
               'label':observations[i]['acquisition_start'][:10]+' → '+observations[j]['acquisition_start'][:10],
               'directory':pair_id,'summary':evidence['summary']}
        manifest['pairs'].append(entry)
        print(f"{pair_id}: {threshold:.3f} dB cutoff; {area:.4f} km²; {len(regions)} regions",flush=True)
    write_json(output/'manifest.json',manifest)
    write_json(output/'config.json',config)
    # Stable filenames for the primary pair and review tools.
    for origin,name in [(output/'t1.tif','before.tif'),(output/'t2.tif','after.tif'),
                         (output/'t1.webp','before.webp'),(output/'t2.webp','after.webp')]:
        shutil.copyfile(origin,output/name)
    for name in ['change_raw.tif','change_mask.tif','change_regions.geojson','change.webp','evidence.json','methodology.json']:
        shutil.copyfile(output/'t1_t2'/name,output/name)
    public=Path('web/public/cases')/config['case_id']; public.mkdir(parents=True,exist_ok=True)
    for path in sorted(output.rglob('*')):
        if path.is_file() and path.suffix in ['.json','.geojson','.webp','.png']:
            target=public/path.relative_to(output); target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    print(f'Artifacts exported to {output} and {public}',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',default='config.json')
    args=parser.parse_args()
    run(args.config)


if __name__=='__main__':
    main()
