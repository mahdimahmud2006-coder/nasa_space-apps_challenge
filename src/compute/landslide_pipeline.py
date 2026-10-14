"""Export separate terrain, rainfall and radar-supported landslide indices on the verified grid."""
import json
from pathlib import Path
import shutil
from affine import Affine
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from src.compute.area import pixel_area_km2
from src.compute.flood_pipeline import json_write,colorize,attention_tiles,sample_summary
from src.compute.flood_model import area_summary
from src.compute.landslide_model import static_features,calculate,spatial_reference_check
from src.compute.timeseries_pipeline import cog
from src.ingest.environment import sha


def run():
    config=json.loads(Path('config.landslide.json').read_text());case=config['case_id'];base=Path('data/derived')/case
    context=json.loads((base/'context/context.json').read_text());timeline=json.loads((base/'timeseries/timeline.json').read_text())
    grid=context['grid'];affine=Affine(*grid['affine']);shape=tuple(grid['shape']);crs=grid['crs'];area=pixel_area_km2(affine,crs)
    directory=base/'landslide';directory.mkdir(exist_ok=True);public=Path('web/public/cases')/case/'landslide';public.mkdir(exist_ok=True)
    inputs={};terrain={}
    def read(path,expected=None,native=False):
        if expected and sha(path)!=expected:raise ValueError('Input hash mismatch: '+str(path))
        inputs[str(path)]=sha(path)
        with rasterio.open(path) as ds:
            if not native and (ds.shape!=shape or ds.transform!=affine or ds.crs.to_string()!=crs):raise ValueError('Context input grid mismatch')
            if native and (ds.transform!=Affine(*timeline['canonical_grid']['affine']) or ds.shape!=tuple(timeline['canonical_grid']['shape']) or ds.crs.to_string()!=crs):raise ValueError('Radar input grid mismatch')
            return ds.read(1)
    for key in ('slope','roughness','curvature','twi','drainage_distance'):
        layer=context['terrain_layers'][key];terrain[key]=read(base/'context'/layer['raster'],layer['sha256'])
    features,bounds=static_features(terrain,config)
    from src.compute.flood_model import weighted_score
    static=weighted_score(features,config['static_weights'])[0]
    cog(directory/'landslide_static.tif',static,affine,crs,'UNCALIBRATED terrain-only landslide attention index 0–100')
    colorize(static,directory/'landslide_static.png')
    flood=json.loads((base/'flood/manifest.json').read_text())
    if sha(base/'flood/components.npz')!=flood['input_hashes']['components']:raise ValueError('Rainfall archive checksum changed')
    inputs[str(base/'flood/components.npz')]=sha(base/'flood/components.npz')
    archive=np.load(base/'flood/components.npz',allow_pickle=False)
    with rasterio.open(base/'timeseries/zone_labels.tif') as ds:labels=ds.read(1)
    observations=[];zone_records=[];reference=None
    for index,obs in enumerate(timeline['observations']):
        identifier=obs['observation_id'];image=read(base/'timeseries'/obs['processed_raster'],native=True)
        if reference is None:reference=image.copy()
        disturbance=None
        if index:
            # Mean ABSOLUTE pixel disturbance, so mixed signed changes cannot cancel.
            block=np.abs(image-reference).reshape(shape[0],3,shape[1],3)
            complete=np.isfinite(block).all(axis=(1,3));disturbance=np.nan_to_num(block).mean(axis=(1,3));disturbance[~complete]=np.nan
        rain={key:archive[identifier+'_'+key] for key in config['rain_reference_mm']}
        score,contributions,weights,components=calculate(features,rain,disturbance,config)
        for key,array in [('dynamic',components['rainfall_trigger']),('total',score),('modifier',components['nisar_modifier'])]:
            if array is None:continue
            cog(directory/(identifier+'_'+key+'.tif'),array,affine,crs,'UNCALIBRATED landslide '+key+' index 0–100')
            colorize(array,directory/(identifier+'_'+key+'.png'))
        common=np.isfinite(score)
        observations.append({'observation_id':identifier,'timestamp':obs['timestamp'],'total_raster':identifier+'_total.tif','total_preview':identifier+'_total.png',
            'dynamic_raster':identifier+'_dynamic.tif','dynamic_preview':identifier+'_dynamic.png',
            'modifier_raster':identifier+'_modifier.tif' if index else None,'modifier_preview':identifier+'_modifier.png' if index else None,
            'summary':area_summary(score,area,boundaries=config['score_boundaries']),
            'component_means':{key:float(array[common].astype('float64').mean()) if array is not None and common.any() else None for key,array in components.items()},
            'contributions':{key:float(array[common].astype('float64').mean()) if common.any() else None for key,array in contributions.items()},
            'effective_weights':weights,'radar_available':index>0,'attention_tiles':attention_tiles(score,area),
            'confidence':None,'confidence_status':'UNVALIDATED','rainfall_window':flood['observations'][index]['rainfall_window']})
        flood_score=read(base/'flood'/flood['observations'][index]['escalation_raster'])
        shared=common & np.isfinite(flood_score)
        observations[-1]['shared_footprint_comparison']={
            'area_km2':float(shared.sum()*area),
            'flood_mean':float(flood_score[shared].astype('float64').mean()) if shared.any() else None,
            'landslide_mean':float(score[shared].astype('float64').mean()) if shared.any() else None,
            'definition':'Both means use the exact same intersected assessable cells; formulas still differ.'}
        for zone in timeline['zones']:
            rr,cc=np.where(labels==zone['id']);rr=rr//3;cc=cc//3
            record=sample_summary(score,contributions,rr,cc,weights,config,zone['zone_id'],obs)
            valid=np.isfinite(score[rr,cc]);record['components']={key:float(array[rr,cc][valid].astype('float64').mean()) if array is not None and valid.any() else None for key,array in components.items()}
            record['interpretation']='Uncalibrated landslide susceptibility index, not a probability, confirmed landslide or early warning.'
            zone_records.append(record)
    references_path=Path('data/context/landslide/references.json')
    refs=json.loads(references_path.read_text()) if references_path.exists() else {'points':[],'status':'NOT_DOWNLOADED'}
    validation=spatial_reference_check(static,refs.get('points',[]),config)
    validation['source_status']=refs.get('status');validation['catalog_points_in_aoi']=len(refs.get('points',[]))
    validation['scope']='Independent historical terrain-only presence review; no empirical validation of the dynamic 2026 model'
    if references_path.exists():inputs[str(references_path)]=sha(references_path)
    json_write(directory/'landslide_validation.json',validation)
    for key in ('dynamic','total'):
        shutil.copy2(directory/(observations[-1]['observation_id']+'_'+key+'.tif'),directory/('landslide_'+key+'.tif'))
    for path in [Path('config.landslide.json'),Path('src/compute/landslide_model.py'),Path('src/compute/landslide_pipeline.py'),base/'context/context.json',base/'timeseries/timeline.json',base/'timeseries/zone_labels.tif']:
        inputs[str(path)]=sha(path)
    model={**config,'normalization_bounds':bounds,'feature_labels':{'static_terrain':'Static terrain','rainfall_trigger':'Prior rainfall trigger','nisar_modifier':'Radar disturbance × slope'},
        'formulas':{'static':'100 × weighted slope, roughness, absolute curvature, TWI and drainage proximity',
            'dynamic':'100 × weighted normalized disjoint 0–24, 24–72 and 72–168 h rain; x/(x+fixed mm reference)',
            'nisar':'100 × min(mean absolute native-pixel baseline dB change / 6,1) × min(slope / 45°,1)',
            'total':'Weighted sum of 0–100 static, dynamic and radar indices. Missing baseline radar omitted with effective weights disclosed.',
            'normalization':'Slope / 45°, drainage exp(-distance/300m); other terrain frozen AOI 2nd/98th percentiles. Design references are uncalibrated.'},
        'training_data_version':None,'confidence':None,'validation_metrics':validation['metrics']}
    manifest={'case_id':case,'status':'UNCALIBRATED_DYNAMIC_LANDSLIDE_SUSCEPTIBILITY','grid':grid,'pixel_area_km2':area,'model':model,
        'observations':observations,'zone_records':zone_records,'static_raster':'landslide_static.tif','static_preview':'landslide_static.png',
        'validation':validation,'reference_catalog':refs,'input_hashes':inputs,
        'limitations':['No calibrated probability, landslide identification, failure time, runout, depth or physical slope-stability simulation.',
            'Illustrative weights and score bands are not calibrated; no supervised training or spatial cross-validation performance is claimed.',
            'Rainfall native detail is regional ~50–60 km, despite the shared 30 m analysis grid.',
            'Historical report geolocation and media/road reporting bias limit independent validation; unreported places are not confirmed negatives.',
            'NASA catalog compilation is independent of these indices; current 2026 dynamic labels remain unavailable.',
            'NASADEM is historical; soil moisture, lithology, faults and land-cover effects are absent.',
            'Absolute NISAR change is ambiguous. Steep-terrain overlap supports attention, not landslide diagnosis.',
            'Radar evidence uses only the baseline and selected visit, never a later acquisition.',
            'No-overlap UNOSAT extent does not establish absence of impacts inside the AOI.']}
    json_write(directory/'manifest.json',manifest)
    pq.write_table(pa.Table.from_pylist(zone_records),directory/'landslide_zones.parquet',compression='zstd')
    for p in directory.iterdir():shutil.copy2(p,public/p.name)
    print('Landslide maps exported:',len(observations),'dates; validation:',validation['status'],flush=True)
    return manifest


if __name__=='__main__':run()
