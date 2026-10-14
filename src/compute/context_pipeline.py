"""Build offline environmental context from downloaded NASA rainfall and terrain."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from affine import Affine
import numpy as np
from PIL import Image, ImageDraw
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from rasterio.warp import reproject, Resampling

from src.compute.environment import accumulation, terrain_derivatives, flow_metrics
from src.compute.timeseries_pipeline import cog
from src.compute.pipeline import code_hash
from src.export.artifacts import write_json
from src.ingest.environment import sha

DEFINITIONS = {
    'dem':('m','NASADEM elevation relative to EGM96 geoid'),
    'slope':('degrees','Slope from centered differences of the original projected DEM'),
    'aspect':('degrees clockwise from north','Downslope direction; flat cells nodata'),
    'curvature':('1/m','Laplacian of elevation, not profile or plan curvature'),
    'roughness':('m','3 x 3 cell elevation population standard deviation'),
    'relative_elevation':('m','Elevation minus local square-window mean; not height above nearest drainage'),
    'flow_accumulation':('m2','D8 upstream contributing area including the cell, bounded by buffered domain'),
    'twi':('dimensionless','ln((contributing_area_m2 / cell_width_m) / (tan(original_slope) + epsilon))'),
    'drainage_distance':('m','Euclidean distance to modeled drainage cells above contributing-area threshold'),
    'fill_depth':('m','Priority-flood depression-fill depth used for routing only'),
    'rain_24h':('mm','Preceding 24 complete hours of NASA POWER liquid-equivalent precipitation'),
    'rain_72h':('mm','Preceding 72 complete hours of NASA POWER liquid-equivalent precipitation'),
    'rain_168h':('mm','Preceding 168 complete hours of NASA POWER liquid-equivalent precipitation'),
}


def project(array, affine, crs, shape, target_affine, target_crs, method=Resampling.nearest):
    result=np.full(shape,np.nan,dtype='float32')
    reproject(array,result,src_transform=affine,src_crs=crs,src_nodata=np.nan,
              dst_transform=target_affine,dst_crs=target_crs,dst_nodata=np.nan,resampling=method)
    return result


def color_preview(path, array, limits):
    valid=np.isfinite(array)
    low,high=limits
    normalized=np.nan_to_num(np.clip((array-low)/max(1e-9,high-low),0,1))
    stops=np.array([[24,47,81],[29,114,133],[89,174,113],[231,216,129],[252,249,229]],dtype='float64')
    positions=np.arange(len(stops))/(len(stops)-1)
    rgb=np.stack([np.interp(normalized,positions,stops[:,channel]) for channel in range(3)],axis=-1)
    rgba=np.concatenate([rgb,valid[...,None]*255],axis=-1).astype('uint8')
    Image.fromarray(rgba).save(path)


def stats(array):
    finite=array[np.isfinite(array)].astype('float64')
    return {'mean':float(finite.mean()) if finite.size else None,
            'min':float(finite.min()) if finite.size else None,
            'max':float(finite.max()) if finite.size else None,
            'valid_fraction':float(finite.size/max(1,array.size))}


def run(config_path='config.context.json'):
    config=json.loads(Path(config_path).read_text());case=config['case_id']
    previous=Path('data/derived')/case/'timeseries'
    timeline=json.loads((previous/'timeline.json').read_text())
    sources=Path(config['sources_directory'])
    rain_source=json.loads((sources/'rainfall_sources.json').read_text())
    terrain_source=json.loads((sources/'terrain_sources.json').read_text())
    for item in terrain_source['items']:
        if sha(item['file'])!=item['sha256']:raise ValueError('NASADEM checksum changed')
    if sha(rain_source['cube_file'])!=rain_source['cube_sha256']:raise ValueError('Rainfall cube checksum changed')
    oldgrid=timeline['canonical_grid'];native=Affine(*oldgrid['affine'])
    resolution=config['context_resolution_m'];factor=round(resolution/native.a)
    if factor<1 or resolution!=factor*native.a or abs(native.e)!=native.a:
        raise ValueError('Context resolution must be an integer multiple of the square native grid')
    if any(s%factor for s in oldgrid['shape']):raise ValueError('Context bounds cannot align exactly')
    shape=tuple(s//factor for s in oldgrid['shape']);affine=native*Affine.scale(factor)
    crs=oldgrid['crs'];halo=round(config['hydrology_buffer_m']/resolution)
    buffered_affine=affine*Affine.translation(-halo,-halo)
    buffered_shape=tuple(s+2*halo for s in shape)
    directory=Path('data/derived')/case/'context';directory.mkdir(parents=True,exist_ok=True)
    print(f'Context grid {shape}, buffered terrain {buffered_shape}',flush=True)
    dem=np.full(buffered_shape,np.nan,dtype='float32')
    for item in terrain_source['items']:
        with rasterio.open(item['file']) as source:
            tile=source.read(1,masked=True).astype('float32').filled(np.nan)
            projected=project(tile,source.transform,source.crs,buffered_shape,buffered_affine,crs,Resampling.bilinear)
            dem[np.isfinite(projected)]=projected[np.isfinite(projected)]
    if not np.isfinite(dem).all():raise ValueError('NASADEM does not cover the full buffered hydrology domain')
    terrain=terrain_derivatives(dem,resolution,config['relative_elevation_radius_m'])
    print('Terrain derivatives ready; filling depressions and routing D8 flow',flush=True)
    flow,hydrology=flow_metrics(dem,resolution,terrain['slope'],config['drainage_threshold_m2'],config['twi_slope_epsilon'])
    crop=(slice(halo,halo+shape[0]),slice(halo,halo+shape[1]))
    terrain={key:value[crop].copy() for key,value in {**terrain,**flow}.items()}
    layers={}

    def export(key,array,filename):
        unit,description=DEFINITIONS[key]
        cog(directory/(filename+'.tif'),array,affine,crs,description+' ('+unit+')')
        limits=[0.,60.] if key=='slope' else ([0.,360.] if key=='aspect' else np.nanpercentile(array,[2,98]).tolist())
        color_preview(directory/(filename+'.png'),array,limits)
        return {'raster':filename+'.tif','preview':filename+'.png','units':unit,'definition':description,
                'display_range':limits,'statistics':stats(array),'sha256':sha(directory/(filename+'.tif'))}

    for key,array in terrain.items():layers[key]=export(key,array,key)
    print('Terrain COGs ready',flush=True)
    cube=np.load(sources/'rainfall.npz',allow_pickle=False)
    rain_affine=Affine(*rain_source['source_grid']['affine'])
    observations=[];rain_arrays={}
    # Shared range per metric makes rainfall maps comparable across dates.
    rain_limits={}
    for observation in timeline['observations']:
        name=observation['observation_id'];date_layers={};windows={}
        for hours in (24,72,168):
            key=f'rain_{hours}h'
            native_total,window=accumulation(cube['times'],cube['rates'],observation['timestamp'],hours, rain_source['bin_duration_seconds'])
            array=project(native_total,rain_affine,'EPSG:4326',shape,affine,crs)
            if not np.isfinite(array).all():raise ValueError('Incomplete rainfall accumulation across the AOI')
            rain_arrays[name,key]=array
            windows[key]=window
            date_layers[key]=export(key,array,name+'_'+key)
            rain_limits[key]=max(rain_limits.get(key,0),float(np.nanmax(array)))
        observations.append({'observation_id':name,'timestamp':observation['timestamp'],
                             'windows':windows,'layers':date_layers})
    for observation in observations:
        for key,layer in observation['layers'].items():
            layer['display_range']=[0,max(1,rain_limits[key])]
            color_preview(directory/layer['preview'],rain_arrays[observation['observation_id'],key],layer['display_range'])
    with rasterio.open(previous/'zone_labels.tif') as ds:
        labels=ds.read(1)
        if ds.transform!=native:raise ValueError('Zone grid disagrees with timeline')
    rows=[]
    for zone in timeline['zones']:
        rr,cc=np.where(labels==zone['id']);context_rows=rr//factor;context_cols=cc//factor
        if len(rr)!=zone['pixel_count']:raise ValueError('Zone label count mismatch')
        cells=context_rows*shape[1]+context_cols
        # Equal-area native pixels weight the fraction of each intersected context cell.
        static={key:stats(array[context_rows,context_cols]) for key,array in terrain.items()}
        for observation in observations:
            name=observation['observation_id']
            rain={key:stats(rain_arrays[name,key][context_rows,context_cols]) for key in ('rain_24h','rain_72h','rain_168h')}
            rows.append({'case_id':case,'zone_id':zone['zone_id'],'observation_id':name,'timestamp':observation['timestamp'],
                'rainfall_mm_24h':rain['rain_24h']['mean'],'max_rainfall_mm_24h':rain['rain_24h']['max'],
                'rainfall_mm_72h':rain['rain_72h']['mean'],'rainfall_mm_168h':rain['rain_168h']['mean'],
                'elevation_m':static['dem']['mean'],'slope_deg':static['slope']['mean'],
                'max_slope_deg':static['slope']['max'],'twi':static['twi']['mean'],
                'distance_to_drainage_m':static['drainage_distance']['mean'],
                'min_distance_to_drainage_m':static['drainage_distance']['min'],
                'native_zone_pixel_count':len(rr),'distinct_terrain_cells':int(np.unique(cells).size),
                'terrain_valid_fraction':static['dem']['valid_fraction'],
                'rainfall_valid_fraction':rain['rain_24h']['valid_fraction'],
                'rainfall_window_end_utc':observation['windows']['rain_24h']['end_exclusive_utc'],
                'rainfall_end_lag_seconds':observation['windows']['rain_24h']['end_lag_seconds'],
                'cause_status':'UNVERIFIED'})
    write_json(directory/'zone_context.json',rows)
    pq.write_table(pa.Table.from_pylist(rows),directory/'context.parquet',compression='zstd')
    limitations=[
        'Context supports interpretation; it does not prove cause.',
        'NASA POWER precipitation is coarse model/reanalysis context at 0.5 latitude by 0.625 longitude degrees (roughly 50–60 km); the 30 m display adds no rainfall detail.',
        'Precipitation totals use complete UTC hours ending before acquisition; requested/end times and lag are recorded. No missing bins are treated as zero.',
        'NASADEM represents historical terrain from the SRTM mission and auxiliary products; it is not an August 2026 terrain survey.',
        'D8 flow, TWI and drainage are model-derived, uncalibrated context within a 12 km buffer; catchments crossing the outer boundary are truncated.',
        'Drainage distance refers to modeled contributing-area channels, not verified mapped rivers.',
        'Priority-flood fills depressions for routing; terrain derivatives use the original DEM. High fill depths can affect hydrologic interpretation.',
        'Zone statistics weight context cells by the count of equal-area 10 m zone pixels they cover; the native source resolution remains unchanged.',
        'No local gauge, surveyed drainage, landslide inventory, or causal validation is supplied. No hazard classification is generated.'
    ]
    manifest={'case_id':case,'status':'ENVIRONMENTAL_CONTEXT_UNVERIFIED','note':limitations[0],
        'generated_utc':datetime.now(timezone.utc).isoformat(),'source_code_sha256':code_hash(),
        'configuration_sha256':sha(config_path),'configuration_file':str(config_path),
        'grid':{'crs':crs,'shape':list(shape),'affine':list(affine)[:6],'resolution_m':resolution,
                'relationship_to_nisar':f'Exact {factor} x {factor} aggregation footprint; existing NISAR remains at {native.a:g} m'},
        'rainfall_source':{k:v for k,v in rain_source.items() if k!='frames'},
        'terrain_source':terrain_source,'terrain_layers':layers,'observations':observations,
        'zone_context':rows,'zone_summary_file':'context.parquet','hydrology':{**hydrology,**{
            'buffer_m':config['hydrology_buffer_m'],'routing':'priority-flood depression fill, deterministic acyclic D8',
            'drainage_threshold_m2':config['drainage_threshold_m2'],'twi_slope_epsilon':config['twi_slope_epsilon'],
            'relative_elevation_window_m':2*config['relative_elevation_radius_m']+resolution}},
        'limitations':limitations+rain_source['limitations'],'zone_sampling':'Equal-area native 10 m zone-pixel centers sampled on aligned 30 m context grid',
        'input_timeline_sha256':sha(previous/'timeline.json'),'input_zone_labels_sha256':sha(previous/'zone_labels.tif')}
    write_json(directory/'context.json',manifest)
    public=Path('web/public/cases')/case/'context';public.mkdir(parents=True,exist_ok=True)
    for path in directory.iterdir():
        if path.is_file():shutil.copy2(path,public/path.name)
    # Side-by-side elevation, slope and modeled drainage for human terrain QA.
    panel=Image.new('RGB',(1200,445),'#101d2a');draw=ImageDraw.Draw(panel)
    for i,(key,title) in enumerate([('dem','Elevation (m, EGM96)'),('slope','Slope (degrees)'),('drainage_distance','Distance to modeled drainage (m)')]):
        image=Image.open(directory/(key+'.png')).convert('RGB').resize((400,400))
        panel.paste(image,(i*400,35));draw.text((i*400+10,12),title,fill='white')
    report=Path('docs/reports');report.mkdir(parents=True,exist_ok=True)
    panel.save(report/'implementation_03_terrain_qa.png')
    print(f'Context complete: {len(rows)} zone-date records, {len(terrain)+len(observations)*3} COGs',flush=True)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',default='config.context.json')
    run(parser.parse_args().config)
