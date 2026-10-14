"""Prepare explainable flood components and the evidence studio's local datasets."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil

from affine import Affine
import numpy as np
from PIL import Image
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.warp import Resampling

from src.compute.area import pixel_area_km2
from src.compute.context_pipeline import project,stats
from src.compute.flood_model import fixed_normalize,normalize_rain,weighted_score,rainfall_features,area_summary,validate_weights
from src.compute.pipeline import code_hash
from src.compute.timeseries_pipeline import cog
from src.ingest.environment import sha

LABELS={'rain_24h':'Rain · last 24 h','rain_24_72h':'Rain · previous 24–72 h',
    'rain_72_168h':'Rain · previous 72–168 h','rain_decay':'Rain · recency weighted',
    'rain_72h':'Rain · last 72 h','terrain_wetness':'Terrain wetness','low_slope':'Low-slope tendency',
    'drainage_proximity':'Modeled drainage proximity','nisar_decrease':'Radar backscatter decrease',
    'decrease_persistence':'Repeated backscatter decrease','static_susceptibility':'Terrain susceptibility',
    'wetness_assumption':'Assumed antecedent wetness','low_elevation':'Low-elevation tendency'}


def json_write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def colorize(values,path,kind='score',limits=(0,100)):
    valid=np.isfinite(values);low,high=limits
    level=np.nan_to_num(np.clip((values-low)/max(1e-6,high-low),0,1))
    palettes={'score':[[19,39,50],[25,104,124],[63,177,157],[247,186,85],[242,104,78],[173,48,72]],
        'delta':[[43,131,196],[146,203,217],[221,228,219],[247,174,103],[218,67,77]],
        'thermal':[[53,66,144],[65,163,176],[226,213,97],[238,127,62],[180,43,60]]}
    stops=np.array(palettes[kind],dtype='float64');positions=np.linspace(0,1,len(stops))
    rgb=np.stack([np.interp(level,positions,stops[:,i]) for i in range(3)],axis=-1)
    rgba=np.concatenate([rgb,valid[...,None]*255],axis=-1).astype('uint8')
    Image.fromarray(rgba).save(path)


def relief(dem,path):
    dy,dx=np.gradient(dem.astype('float64'),30)
    normal=np.stack([-dx,dy,np.ones_like(dem)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    light=np.array([-.5,.5,.7071068]);intensity=np.clip((normal*light).sum(axis=-1),0,1)
    relative=fixed_normalize(dem,*np.nanpercentile(dem,[2,98]))
    low=np.array([28,51,58]);high=np.array([161,168,142]);rgb=low+(high-low)*relative[...,None]
    rgb*=.5+.55*intensity[...,None]
    Image.fromarray(np.clip(rgb,0,255).astype('uint8')).save(path)


def sample_summary(score,components,rows,cols,weights,model,identifier,timestamp):
    valid=np.isfinite(score[rows,cols]);coverage=float(valid.mean()) if valid.size else 0
    contribution={key:float(array[rows,cols][valid].astype('float64').mean()) for key,array in components.items()} if valid.any() else {}
    value=sum(contribution.values()) if contribution else None
    index=int(np.digitize(value,model['score_boundaries'])) if value is not None else None
    return {'zone_id':identifier,'observation_id':timestamp['observation_id'],'timestamp':timestamp['timestamp'],
        'score':value,'class':model['score_classes'][index] if index is not None else 'Not assessable',
        'contributions':contribution,'effective_weights':weights,'coverage_fraction':coverage,
        'confidence':None,'confidence_status':'UNVALIDATED','model_version':model['model_version'],
        'interpretation':'Uncalibrated attention index; not a flood probability or confirmed flood classification.'}


def attention_tiles(score,pixel_area,size=40,limit=12,high_threshold=50):
    rows=[]
    for y in range(0,score.shape[0],size):
        for x in range(0,score.shape[1],size):
            array=score[y:y+size,x:x+size];valid=np.isfinite(array)
            if valid.mean()<.8:continue
            rows.append({'tile_id':f'GRID-{y//size+1:02d}-{x//size+1:02d}',
                'row_start':y,'col_start':x,'height':array.shape[0],'width':array.shape[1],
                'mean_score':float(array[valid].astype('float64').mean()),
                'high_area_km2':float((valid&(array>=high_threshold)).sum()*pixel_area),
                'coverage_fraction':float(valid.mean()),'unit':'Analysis tile; not a settlement or exposure estimate'})
    rows.sort(key=lambda row:(-row['mean_score'],row['tile_id']))
    return rows[:limit]


def run():
    config=json.loads(Path('config.flood.json').read_text());case=config['case_id']
    for name in ('static_weights','escalation_weights','scenario_weights'):validate_weights(config[name])
    base=Path('data/derived')/case;context=json.loads((base/'context/context.json').read_text())
    timeline=json.loads((base/'timeseries/timeline.json').read_text());grid=context['grid']
    affine=Affine(*grid['affine']);crs=grid['crs'];shape=tuple(grid['shape']);pixel_area=pixel_area_km2(affine,crs)
    directory=base/'flood';directory.mkdir(exist_ok=True)
    public=Path('web/public/cases')/case/'flood';public.mkdir(exist_ok=True)
    arrays={}
    for key in ('dem','slope','twi','drainage_distance'):
        layer=context['terrain_layers'][key];path=base/'context'/layer['raster']
        if sha(path)!=layer['sha256']:raise ValueError('Context terrain source checksum changed')
        with rasterio.open(path) as ds:
            if ds.transform!=affine or ds.shape!=shape or ds.crs.to_string()!=crs:raise ValueError('Terrain input grid mismatch')
            arrays[key]=ds.read(1)
    norms={key:np.nanpercentile(arrays[key],[2,98]).tolist() for key in ('dem','twi')}
    components={
        'low_elevation':fixed_normalize(arrays['dem'],*norms['dem'],invert=True),
        'low_slope':1-np.clip(arrays['slope']/config['slope_reference_deg'],0,1),
        'terrain_wetness':fixed_normalize(arrays['twi'],*norms['twi']),
        'drainage_proximity':np.exp(-arrays['drainage_distance']/config['drainage_scale_m'])}
    static,_,_=weighted_score(components,config['static_weights']);components['static_susceptibility']=static/100
    cog(directory/'static_susceptibility.tif',static,affine,crs,'Uncalibrated terrain-only susceptibility index 0–100')
    relief(arrays['dem'],directory/'relief.png')
    from scipy.ndimage import map_coordinates
    rr,cc=np.meshgrid(np.linspace(-.5,shape[0]-.5,101),np.linspace(-.5,shape[1]-.5,101),indexing='ij')
    mesh=map_coordinates(arrays['dem'],[rr,cc],order=1,mode='nearest').astype('float64')
    json_write(directory/'terrain_mesh.json',{'heights_m':np.round(mesh,1).tolist(),'spacing_m':240,
        'width_m':shape[1]*30,'height_m':shape[0]*30,'min_elevation_m':float(np.nanmin(arrays['dem'])),
        'vertical_reference':'EGM96 geoid','source':'NASADEM HGT v001','display_only':True})
    from shapely.geometry import box,mapping
    from src.compute.validation_context import official_extent,SOURCE_URL
    mapped,digest,ring_count=official_extent('data/context/unosat_20260826_flood_extent.zip')
    study=box(*rasterio.transform.array_bounds(*shape,affine))
    geographic={'source_url':SOURCE_URL,'source_archive_sha256':digest,'source_type':'Preliminary UNOSAT mudflow/rockflow impact mapping, not open-water extent',
        'overlap_area_km2':mapped.intersection(study).area/1e6,'closest_mapped_distance_km':mapped.distance(study)/1000,
        'study_geometry_projected':mapping(study),'mapped_geometry_projected':mapping(mapped.simplify(80,preserve_topology=True)),
        'crs':crs,'display_simplification_m':80,'intersection_uses_unsimplified_geometry':True,
        'event_mechanism_source':'https://www.who.int/nepal/emergencies/2026-rasuwa-flash-floods',
        'interpretation':'Available impact mapping provides no spatial validation inside this study AOI. No absence of physical impacts is inferred.',
        'model_scope':'Rainfall-driven susceptibility does not model upstream ice avalanches, impoundment breaches, debris flows or flood-wave hydraulics.'}
    json_write(directory/'geographic_check.json',geographic)
    native_rain=np.load('data/context/environment/rainfall.npz',allow_pickle=False)
    rain_source=json.loads(Path('data/context/environment/rainfall_sources.json').read_text())
    if sha(rain_source['cube_file'])!=rain_source['cube_sha256']:raise ValueError('Rainfall source checksum changed')
    rain_affine=Affine(*rain_source['source_grid']['affine'])
    native_images=[];reference=None;decrease_count=np.zeros(shape,dtype='float32');decrease_valid=np.ones(shape,dtype=bool)
    archive={**components,'elevation_m':arrays['dem'],'slope_deg':arrays['slope'],'twi':arrays['twi'],'drainage_distance_m':arrays['drainage_distance'],'rain_times':native_rain['times'],'rain_rates':native_rain['rates']}
    observations=[];zone_records=[]
    with rasterio.open(base/'timeseries/zone_labels.tif') as ds:zone_labels=ds.read(1)
    for index,observation in enumerate(timeline['observations']):
        identifier=observation['observation_id']
        with rasterio.open(base/'timeseries'/observation['processed_raster']) as ds:
            image=ds.read(1)
            if ds.crs.to_string()!=crs or ds.transform!=Affine(*timeline['canonical_grid']['affine']):raise ValueError('Radar grid mismatch')
        if reference is None:reference=image.copy()
        if index:
            delta=image-reference
            blocks=delta.reshape(shape[0],3,shape[1],3)
            valid=np.isfinite(blocks).all(axis=(1,3));mean=np.nan_to_num(blocks).mean(axis=(1,3));mean[~valid]=np.nan
            radar=np.clip(-mean/config['radar_decrease_scale_db'],0,1).astype('float32')
            decrease_count+=np.where(valid,mean<=-config['radar_persistence_threshold_db'],0)
            decrease_valid &=valid
            frequency=decrease_count/index;frequency[~decrease_valid]=np.nan
        else:radar=None;frequency=None
        # Persistence uses only dates at/before this observation, never the complete future series.
        features={**components,'nisar_decrease':radar,'decrease_persistence':frequency}
        archive[identifier+'_nisar']=radar if radar is not None else np.full(shape,np.nan,dtype='float32')
        archive[identifier+'_persistence']=frequency.copy() if frequency is not None else np.full(shape,np.nan,dtype='float32')
        rain,window=rainfall_features(native_rain['times'],native_rain['rates'],observation['timestamp'],config['rain_half_life_hours'])
        for key,ref in config['rain_reference_mm'].items():
            value=project(rain[key],rain_affine,'EPSG:4326',shape,affine,crs)
            archive[identifier+'_'+key]=value
            features[key]=normalize_rain(value,ref)
        score,contributions,effective=weighted_score(features,config['escalation_weights'])
        cog(directory/(identifier+'_escalation.tif'),score,affine,crs,'Uncalibrated explainable flood escalation attention index, 0–100')
        colorize(score,directory/(identifier+'_escalation.png'))
        summary=area_summary(score,pixel_area,boundaries=config['score_boundaries'])
        observations.append({'observation_id':identifier,'timestamp':observation['timestamp'],
            'escalation_raster':identifier+'_escalation.tif','escalation_preview':identifier+'_escalation.png',
            'summary':summary,'contributions':{key:float(value[np.isfinite(score)].astype('float64').mean()) for key,value in contributions.items()},'effective_weights':effective,'rainfall_window':window,
            'radar_available':index>0,'attention_tiles':attention_tiles(score,pixel_area,config['attention_tile_pixels'],high_threshold=config['score_boundaries'][1]),
            'confidence':None,'confidence_status':'UNVALIDATED'})
        for zone in timeline['zones']:
            rr,cc=np.where(zone_labels==zone['id']);rr=rr//3;cc=cc//3
            record=sample_summary(score,contributions,rr,cc,effective,config,zone['zone_id'],observation)
            record.update({'data_quality':{'rainfall_native_grid':'0.5° latitude × 0.625° longitude',
                'terrain_grid_m':30,'model_calibrated':False,'history_available':False},
                'raw_features':{key:float(archive[identifier+'_'+key][rr,cc].astype('float64').mean()) for key in config['rain_reference_mm']}})
            zone_records.append(record)
        print('Escalation prepared:',identifier,summary,flush=True)
    np.savez_compressed(directory/'components.npz',**archive)
    input_records={'context_json':sha(base/'context/context.json'),'timeline_json':sha(base/'timeseries/timeline.json'),
        'rainfall_cube':rain_source['cube_sha256'],'components':sha(directory/'components.npz'),'model_configuration':sha('config.flood.json'),
        'model_source':sha('src/compute/flood_model.py'),'engine_source':sha('src/compute/flood_engine.py'),
        'pipeline_source':sha('src/compute/flood_pipeline.py')}
    inputs_sha=hashlib.sha256(json.dumps(input_records,sort_keys=True).encode()).hexdigest()
    model={**config,'created_utc':datetime.now(timezone.utc).isoformat(),'training_data_version':None,
        'validation_metrics':{name:None for name in ('precision','recall','f1','roc_auc','pr_auc','brier_score','calibration_curve')},
        'validation_reason':'No independently labeled training/validation flood cases. These metrics and confidence are not fabricated.',
        'feature_labels':LABELS,'feature_list':list(config['escalation_weights']),'scenario_feature_list':list(config['scenario_weights']),'normalization':{'terrain_robust_bounds':norms,
            'rainfall':'x / (x + fixed reference mm); fixed before scenarios, not renormalized per run',
            'rainfall_disjoint_windows':True,'rainfall_decay_half_life_hours':config['rain_half_life_hours'],
            'rainfall_references_are':'Illustrative model design values, not validated Nepal flood thresholds'},
        'historical_response':{'available':False,'reason':'A single independent extent review is not repeated flood response history.'},
        'confidence':{'value':None,'status':'UNVALIDATED','reason':'Coverage is reported separately; no empirical model confidence exists.'}}
    limits=['Available UNOSAT mudflow/rockflow mapping has zero overlap with this study AOI; it does not validate scores here or prove absence of impact.',
        'This rainfall-driven model does not reconstruct the reported upstream ice-avalanche/damming mechanism of the August 26 event.',
        'Uncalibrated susceptibility indices, not flood probabilities, flood depths, velocities, forecasts or confirmed flood extents.',
        'Counterfactual scenarios multiply rainfall in the selected previous 6–72 complete hours; they do not simulate future rainfall.',
        'POWER rainfall is regional model/reanalysis context at roughly 50–60 km; 30 m maps add no rainfall detail.',
        'Thermal imagery is independent context and is not used as a flood predictor in this model.',
        'Terrain wetness and drainage are model-derived and bounded by the existing 12 km hydrology buffer.',
        'Backscatter decrease and repetition are ambiguous; they do not establish water, flood cause, or persistent inundation.',
        'No exposure assets or population are supplied; newly high area describes model categories, not people or buildings exposed.',
        'Scores use illustrative weights; correlated predictors and score thresholds have not been empirically validated.',
        'Missing globally unavailable radar/history features are omitted with effective weights disclosed. Missing spatial pixels remain nodata.',
        'Historical context artifacts retain their original generation fingerprints; new modules do not retroactively change their producing code.']
    native_ids=np.arange(4,dtype='float32').reshape(2,2)
    placed_ids=project(native_ids,rain_affine,'EPSG:4326',shape,affine,crs).astype('int32')
    cell_weights=np.bincount(placed_ids.ravel(),minlength=4)/placed_ids.size
    daily=[]
    for i in range(0,len(native_rain['times']),24):
        block=native_rain['rates'][i:i+24]
        if len(block)!=24:continue
        totals=block.sum(axis=0);daily.append({'date':datetime.fromtimestamp(int(native_rain['times'][i]),timezone.utc).strftime('%Y-%m-%d'),
            'aoi_mean_mm':float(np.dot(totals.ravel(),cell_weights)),'cell_totals_mm':totals.tolist(),
            'definition':'Area-weighted mean of regional POWER cells over projected AOI; not a gauge measurement'})
    manifest={'case_id':case,'status':'UNCALIBRATED_SCENARIO_AND_ATTENTION_INDEX','grid':grid,'pixel_area_km2':pixel_area,
        'model':model,'geographic_check':{k:v for k,v in geographic.items() if 'geometry' not in k},'observations':observations,'zone_records':zone_records,'rainfall_daily':daily,'rainfall_source_cell_area_weights':cell_weights.tolist(),
        'input_hashes':input_records,'inputs_sha256':inputs_sha,'source_code_sha256':code_hash(),
        'rainfall_source':rain_source,'limitations':limits,'relief_preview':'relief.png','terrain_mesh':'terrain_mesh.json'}
    json_write(directory/'manifest.json',manifest);json_write(directory/'model.json',model)
    pq.write_table(pa.Table.from_pylist([{k:v for k,v in row.items() if k not in ('data_quality','raw_features')} for row in zone_records]),directory/'flood_escalation.parquet',compression='zstd')
    for path in directory.iterdir():
        if path.suffix in ('.json','.png','.tif','.parquet'):shutil.copy2(path,public/path.name)
    from src.compute.flood_engine import get_engine
    engine=get_engine(Path.cwd(),case)
    for observation in observations:
        for multiplier,wetness in [(1.,'normal'),(1.25,'wet'),(1.5,'wet'),(2.,'wet')]:
            engine.scenario({'observation_id':observation['observation_id'],'rainfall_multiplier':multiplier,
                            'duration_hours':48,'wetness':wetness})
    print('Flood model components, exports and 12 cached scenarios ready',flush=True)
    return manifest


if __name__=='__main__':run()
