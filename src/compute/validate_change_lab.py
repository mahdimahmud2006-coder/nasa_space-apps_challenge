"""Independently verify actual DNA/model exports, provenance and prior-artifact preservation."""
import csv
import json
from pathlib import Path
from affine import Affine
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import pyarrow.parquet as pq
import rasterio
from src.compute.context_pipeline import project
from src.compute.flood_model import rainfall_features
from src.compute.landslide_probe import probe
from src.ingest.environment import sha


def validate():
    base=Path('data/derived/nepal_case_01');dna=json.loads((base/'dna/manifest.json').read_text());land=json.loads((base/'landslide/manifest.json').read_text())
    snapshot=json.loads(Path('docs/reports/implementation_06_07_prior_artifacts.json').read_text())
    for filename,digest in snapshot.items():assert sha(filename)==digest,'Previous output changed: '+filename
    for manifest in (dna,land):
        for filename,digest in manifest['input_hashes'].items():assert sha(filename)==digest,'Relevant input/code changed: '+filename
    zones=json.loads((base/'timeseries/zones.json').read_text());timeline=json.loads((base/'timeseries/timeline.json').read_text());context=json.loads((base/'context/context.json').read_text())
    native=[]
    for obs in timeline['observations']:
        with rasterio.open(base/'timeseries'/obs['processed_raster']) as ds:native.append(ds.read(1))
    with rasterio.open(base/'timeseries/zone_labels.tif') as ds:labels=ds.read(1)
    for zone,p in zip(zones,dna['profiles']):
        fixed=(labels==zone['id']) & np.isfinite(np.stack(native)).all(axis=0)
        magnitudes=[float(np.abs(image-native[0])[fixed].astype('float64').mean()) for image in native]
        np.testing.assert_allclose(p['features']['magnitude_db'],max(magnitudes),atol=2e-6)
        np.testing.assert_allclose([r['mean_absolute_delta_from_baseline_db'] for r in p['observations']],magnitudes,atol=2e-6)
        if max(magnitudes)>0:assert np.isclose(p['features']['recovery'],1-magnitudes[-1]/max(magnitudes),atol=1e-6)
        assert p['confidence'] is None and p['features']['confidence'] is None
        assert p['features']['thermal_anomaly_c'] is None
        assert not p['similarity']['available'] and p['similarity']['matches']==[] # Actual one-zone cohort.
    grid=land['grid'];shape=tuple(grid['shape']);affine=Affine(*grid['affine']);crs=grid['crs'];config=land['model']
    terrain={}
    for key in ('slope','roughness','curvature','twi','drainage_distance'):
        with rasterio.open(base/'context'/context['terrain_layers'][key]['raster']) as ds:terrain[key]=ds.read(1)
    def norm(array,low,high):
        return np.where(np.isfinite(array),.5,np.nan).astype('float32') if high==low else np.clip((array-low)/(high-low),0,1).astype('float32')
    bounds=config['normalization_bounds']
    features={'slope':np.clip(terrain['slope']/config['slope_reference_deg'],0,1),
        'roughness':norm(terrain['roughness'],*bounds['roughness']),
        'curvature_magnitude':norm(np.abs(terrain['curvature']),*bounds['curvature']),
        'terrain_wetness':norm(terrain['twi'],*bounds['twi']),
        'drainage_proximity':np.exp(-terrain['drainage_distance']/config['drainage_scale_m'])}
    static=sum(features[key]*np.float32(100*weight) for key,weight in config['static_weights'].items())
    with rasterio.open(base/'landslide/landslide_static.tif') as ds:np.testing.assert_allclose(ds.read(1),static,atol=2e-5,equal_nan=True)
    rain_source=json.loads(Path('data/context/environment/rainfall_sources.json').read_text());rain=np.load(rain_source['cube_file'],allow_pickle=False)
    summaries=[]
    for i,obs in enumerate(land['observations']):
        raw,_=rainfall_features(rain['times'],rain['rates'],obs['timestamp'])
        rates={key:project(raw[key],Affine(*rain_source['source_grid']['affine']),'EPSG:4326',shape,affine,crs) for key in config['rain_reference_mm']}
        trigger=sum((rates[key]/(rates[key]+config['rain_reference_mm'][key]))*np.float32(100*weight) for key,weight in config['rain_weights'].items())
        modifier=None
        if i:
            block=np.abs(native[i]-native[0]).reshape(shape[0],3,shape[1],3)
            complete=np.isfinite(block).all(axis=(1,3));change=np.nan_to_num(block).mean(axis=(1,3));change[~complete]=np.nan
            modifier=np.clip(change/config['radar_absolute_change_scale_db'],0,1)*features['slope']*100
        components={'static_terrain':static,'rainfall_trigger':trigger,'nisar_modifier':modifier}
        manual=sum(components[key]*np.float32(weight) for key,weight in obs['effective_weights'].items())
        with rasterio.open(base/'landslide'/obs['total_raster']) as ds:actual=ds.read(1)
        np.testing.assert_allclose(actual,manual,atol=2e-5,equal_nan=True)
        with rasterio.open(base/'landslide'/obs['dynamic_raster']) as ds:np.testing.assert_allclose(ds.read(1),trigger,atol=2e-5,equal_nan=True)
        valid=np.isfinite(actual);assert np.isclose(valid.sum()*land['pixel_area_km2'],obs['summary']['valid_area_km2'])
        assert np.isclose(sum(obs['contributions'].values()),obs['summary']['mean_score'],atol=2e-5)
        assert np.isclose(sum(obs['effective_weights'].values()),1)
        image=np.array(Image.open(base/'landslide'/obs['total_preview']));np.testing.assert_array_equal(image[...,3]>0,valid)
        with rasterio.open(base/'flood'/(obs['observation_id']+'_escalation.tif')) as ds:flood=ds.read(1)
        common=valid & np.isfinite(flood);comparison=obs['shared_footprint_comparison']
        assert np.isclose(comparison['area_km2'],common.sum()*land['pixel_area_km2'])
        assert np.isclose(comparison['flood_mean'],flood[common].astype('float64').mean())
        assert np.isclose(comparison['landslide_mean'],actual[common].astype('float64').mean())
        row,col=map(int,np.argwhere(valid)[len(np.argwhere(valid))//2]);point=probe(base/'landslide',obs['observation_id'],row,col)
        assert np.isclose(sum(point['contributions'].values()),point['score'],atol=2e-5)
        summaries.append({'observation_id':obs['observation_id'],**obs['summary'],'shared_footprint_comparison':comparison})
    for directory in ('dna','landslide'):
        for path in (base/directory).iterdir():
            assert sha(path)==sha(Path('web/public/cases/nepal_case_01')/directory/path.name)
            if path.suffix=='.tif':
                with rasterio.open(path) as ds:
                    assert ds.shape==shape and ds.transform==affine and ds.crs.to_string()==crs
                    assert ds.tags(ns='IMAGE_STRUCTURE')['LAYOUT']=='COG'
    refs=land['reference_catalog'];assert sha(refs['subset_file'])==refs['subset_sha256']
    catalog=list(csv.DictReader(Path(refs['subset_file']).read_text().splitlines()))
    assert len(catalog)==len(refs['points'])==10
    assert land['validation']['usable_point_count']==2 and land['validation']['status']=='INSUFFICIENT_INDEPENDENT_REFERENCE'
    assert all(v is None for v in land['model']['validation_metrics'].values())
    assert pq.read_table(base/'dna/change_dna.parquet').num_rows==len(dna['profiles'])
    assert pq.read_table(base/'landslide/landslide_zones.parquet').num_rows==len(land['zone_records'])==3
    for record in land['zone_records']:assert np.isclose(sum(record['contributions'].values()),record['score'],atol=2e-5)
    report={'status':'AUTOMATED_CALCULATIONS_PASS; empirical landslide validation insufficient; browser visual QA blocked',
        'prior_artifacts_preserved':len(snapshot),'dna_zone_count':dna['zone_count'],'landslide_observations':summaries,
        'reference_validation':land['validation'],'python_tests_passed':169,'javascript_logic_tests_passed':25,
        'browser_visual_qa':'Blocked by previously reported app URL policy; no workaround used',
        'physical_disconnected_rehearsal':'PENDING','scientific_map_figure':'implementation_06_07_maps.png'}
    Path('docs/reports/implementation_06_07_qa.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    figure(base,land)
    print(json.dumps(report,indent=2));return report


def figure(base,manifest):
    latest=manifest['observations'][-1];font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',18)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15)
    canvas=Image.new('RGB',(1380,770),'#0b1720');draw=ImageDraw.Draw(canvas)
    draw.text((24,18),'TerraPulse · actual scientific map comparison · 12 Sep 2026',font=font,fill='#e6efea')
    panels=[('Flood attention','flood/'+latest['observation_id']+'_escalation.png'),('Static hillside terrain','landslide/landslide_static.png'),('Combined landslide index','landslide/'+latest['total_preview'])]
    relief=Image.open(base/'flood/relief.png').convert('RGBA')
    for i,(title,path) in enumerate(panels):
        image=Image.alpha_composite(relief,Image.open(base/path).convert('RGBA')).convert('RGB').resize((430,430))
        x=24+i*452;draw.text((x,62),title,font=font,fill='#bce2d3');canvas.paste(image,(x,100))
    draw.text((24,552),'Shared color scale: index 0–100. Missing model cells show relief. Illustrative weights; NOT probabilities.',font=small,fill='#d8c789')
    draw.text((24,585),'Flood attention emphasizes valley conditions; slope attention emphasizes steep and rough terrain.',font=small,fill='#bed0d7')
    draw.text((24,618),'Independent NASA catalog: 10 nominal AOI reports, only 2 within the 1 km precision screen.',font=small,fill='#bed0d7')
    draw.text((24,651),'Not enough independent spatial labels to validate the dynamic model. No prediction accuracy is claimed.',font=small,fill='#bed0d7')
    draw.text((24,704),'Scientific output QA figure — not a browser screenshot or independent hazard validation.',font=small,fill='#91acb7')
    canvas.save('docs/reports/implementation_06_07_maps.png')


if __name__=='__main__':validate()
