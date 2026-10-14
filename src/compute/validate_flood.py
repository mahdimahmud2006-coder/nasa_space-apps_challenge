"""Check real model/thermal outputs, monotonicity, temporal integrity and preservation."""
import json
from pathlib import Path
from time import perf_counter

from affine import Affine
import numpy as np
from PIL import Image,ImageDraw
import pyarrow.parquet as pq
import rasterio

from src.compute.context_pipeline import project
from src.compute.flood_engine import get_engine
from src.compute.flood_model import weighted_score,normalize_rain,rainfall_features,area_summary
from src.compute.thermal_pipeline import quality_mask
from src.ingest.environment import sha
from src.ingest.thermal import validate_url


def validate():
    root=Path.cwd();base=root/'data/derived/nepal_case_01';directory=base/'flood'
    manifest=json.loads((directory/'manifest.json').read_text());thermal=json.loads((base/'thermal/manifest.json').read_text())
    grid=manifest['grid'];affine=Affine(*grid['affine']);shape=tuple(grid['shape']);crs=grid['crs']
    archive=np.load(directory/'components.npz',allow_pickle=False)
    assert sha(directory/'components.npz')==manifest['input_hashes']['components']
    for name,filename in [('model_source','src/compute/flood_model.py'),('engine_source','src/compute/flood_engine.py'),('pipeline_source','src/compute/flood_pipeline.py')]:
        assert manifest['input_hashes'][name]==sha(filename),'Relevant model source changed; run make flood'
    previous=json.loads(Path('docs/reports/implementation_04_05_prior_artifacts.json').read_text())
    for filename,digest in previous.items():assert sha(filename)==digest,'Previous artifact changed: '+filename
    assert thermal['source']['producer_organizations']==['USGS','NASA']
    counts=[]
    for scene in thermal['scenes']:
        arrays={}
        for asset in scene['assets']:
            validate_url(asset['url']);assert sha(asset['file'])==asset['sha256']
            with rasterio.open(asset['file']) as ds:
                arrays[asset['key']]=project(ds.read(1).astype('float32'),ds.transform,ds.crs,shape,affine,crs)
        mask,uncertainty=quality_mask(arrays['lwir11'],np.nan_to_num(arrays['qa_pixel'],nan=1),arrays['qa_radsat'],arrays['qa'],max_uncertainty_k=5)
        expected=arrays['lwir11']*.00341802+149.-273.15;expected[~mask]=np.nan
        with rasterio.open(base/'thermal'/scene['temperature_raster']) as ds:
            assert ds.transform==affine and ds.shape==shape and ds.crs.to_string()==crs
            assert ds.tags(ns='IMAGE_STRUCTURE')['LAYOUT']=='COG'
            actual=ds.read(1)
        np.testing.assert_array_equal(actual,expected)
        assert np.isclose(np.isfinite(actual).mean(),scene['valid_fraction'])
        assert np.nanmax(uncertainty[mask])<=5
        assert scene['strict_3k_valid_fraction']==0 # Actual downloaded event-period scenes, not generalized to other scenes.
        image=np.array(Image.open(base/'thermal'/scene['preview']))
        np.testing.assert_array_equal(image[...,3]>0,np.isfinite(actual))
        assert sha(base/'thermal'/scene['temperature_raster'])==sha(root/'web/public/cases/nepal_case_01/thermal'/scene['temperature_raster'])
        counts.append({'date':scene['datetime'][:10],'valid_fraction':scene['valid_fraction'],'mean_temperature_c':scene['statistics_celsius']['mean'],
                       'mean_reported_uncertainty_k':scene['uncertainty_statistics_k']['mean']})
    # Independently reproduce radar decrease and repetition using only earlier/current dates.
    reference=None;count=np.zeros(shape,dtype='float32');common=np.ones(shape,dtype=bool)
    for i,ob in enumerate(manifest['observations']):
        with rasterio.open(base/'timeseries'/f'nisar_t{i+1}.tif') as ds:image=ds.read(1)
        if i==0:
            reference=image;assert np.isnan(archive[ob['observation_id']+'_nisar']).all();continue
        delta=(image-reference).reshape(shape[0],3,shape[1],3)
        valid=np.isfinite(delta).all(axis=(1,3));mean=np.nan_to_num(delta).mean(axis=(1,3));mean[~valid]=np.nan
        radar=np.clip(-mean/manifest['model']['radar_decrease_scale_db'],0,1)
        np.testing.assert_array_equal(radar,archive[ob['observation_id']+'_nisar'])
        count+=np.where(valid,mean<=-manifest['model']['radar_persistence_threshold_db'],0);common &=valid
        expected=count/i;expected[~common]=np.nan
        np.testing.assert_array_equal(expected,archive[ob['observation_id']+'_persistence'])
    for ob in manifest['observations']:
        identifier=ob['observation_id']
        features={key:archive[key] for key in ('terrain_wetness','low_slope','drainage_proximity')}
        for key,reference_mm in manifest['model']['rain_reference_mm'].items():
            raw=archive[identifier+'_'+key];features[key]=raw/(raw+reference_mm)
        if ob['radar_available']:
            features['nisar_decrease']=archive[identifier+'_nisar']
            features['decrease_persistence']=archive[identifier+'_persistence']
        manual=np.zeros(shape,dtype='float32');valid=np.ones(shape,dtype=bool)
        for key,weight in ob['effective_weights'].items():
            component=features[key]*np.float32(weight*100);valid &=np.isfinite(component)
            manual+=np.nan_to_num(component)
        manual[~valid]=np.nan
        with rasterio.open(directory/ob['escalation_raster']) as ds:
            assert ds.transform==affine and ds.tags(ns='IMAGE_STRUCTURE')['LAYOUT']=='COG'
            np.testing.assert_allclose(ds.read(1),manual,atol=2e-5,equal_nan=True)
        assert np.isclose(manual[valid].astype('float64').mean(),ob['summary']['mean_score'])
        assert np.isclose(sum(ob['contributions'].values()),ob['summary']['mean_score'],atol=2e-5)
    for row in manifest['zone_records']:
        assert row['confidence'] is None and row['confidence_status']=='UNVALIDATED'
        assert np.isclose(sum(row['contributions'].values()),row['score'],atol=1e-5)
        assert np.isclose(sum(row['effective_weights'].values()),1)
    assert all(value is None for value in manifest['model']['validation_metrics'].values())
    assert not manifest['model']['historical_response']['available']
    engine=get_engine(root,'nepal_case_01');metrics=[]
    latest=engine.ids[-1]
    for multiplier in (.5,1,1.5,2,3):
        params={'observation_id':latest,'rainfall_multiplier':multiplier,'duration_hours':48,'wetness':'normal','historical_sensitivity':False}
        score,components,_,_=engine.calculate(params)
        np.testing.assert_allclose(score,sum(components.values()),atol=2e-5,equal_nan=True)
        if metrics:
            valid=np.isfinite(score)&np.isfinite(last)
            assert np.all(score[valid]>=last[valid]-1e-5),'Increasing rainfall reduced susceptibility'
        last=score.copy();metrics.append({'multiplier':multiplier,**area_summary(score,engine.area)})
    one=engine.calculate({'observation_id':latest,'rainfall_multiplier':1.,'duration_hours':6,'wetness':'normal'})[0]
    long=engine.calculate({'observation_id':latest,'rainfall_multiplier':1.,'duration_hours':72,'wetness':'normal'})[0]
    np.testing.assert_array_equal(one,long)
    params={'observation_id':latest,'rainfall_multiplier':1.5,'duration_hours':48,'wetness':'wet'}
    start=perf_counter();result=engine.scenario(params);cached_ms=(perf_counter()-start)*1000
    assert result==engine.scenario(dict(reversed(list(params.items()))))
    path=root/'web/public/cases'/result['raster_url'].removeprefix('/cases/')
    with rasterio.open(path) as ds:
        assert ds.transform==affine and ds.crs.to_string()==crs and ds.tags(ns='IMAGE_STRUCTURE')['LAYOUT']=='COG'
        score=ds.read(1)
    expected=engine.calculate({**params,'historical_sensitivity':False})[0]
    np.testing.assert_array_equal(score,expected)
    summary=area_summary(score,engine.area,engine.baseline(latest)[0])
    for key,value in summary.items():assert np.isclose(value,result['summary'][key])
    assert result['generation_ms']<2000 or cached_ms<2000
    geography=json.loads((directory/'geographic_check.json').read_text())
    assert geography['overlap_area_km2']==0 and geography['closest_mapped_distance_km']>0
    assert np.isclose(sum(manifest['rainfall_source_cell_area_weights']),1)
    assert pq.read_table(directory/'flood_escalation.parquet').num_rows==len(manifest['zone_records'])
    # Scientific map comparison only; this is not a browser screenshot.
    panels=[('Unmodified rain / normal wetness assumed',root/'web/public/cases'/result['baseline_preview_url'].removeprefix('/cases/')),
            ('Counterfactual 1.5x / 48h / wet',root/'web/public/cases'/result['preview_url'].removeprefix('/cases/')),
            ('Landsat thermal: 19 Sep 2026',base/'thermal'/thermal['scenes'][-1]['preview'])]
    figure=Image.new('RGB',(1500,555),'#0b1720');draw=ImageDraw.Draw(figure)
    relief=Image.open(directory/'relief.png').convert('RGBA').resize((500,500))
    for i,(title,path) in enumerate(panels):
        image=Image.open(path).convert('RGBA').resize((500,500));composition=Image.alpha_composite(relief,image).convert('RGB')
        figure.paste(composition,(i*500,35));draw.text((i*500+12,12),title,fill='#d9e9e3')
    draw.text((12,538),'Uncalibrated indices, not flood extent. Thermal gaps show the terrain background; temperature is land surface, not air.',fill='#9eb9be')
    figure.save('docs/reports/implementation_04_05_map_comparison.png')
    report={'status':'PASS','prior_artifacts_unchanged':len(previous),'thermal_scenes':counts,
        'escalation_observations':len(manifest['observations']),'zone_records':len(manifest['zone_records']),
        'monotonicity_scenarios':metrics,'example_scenario':result['summary'],'example_generation_ms':result['generation_ms'],
        'cached_request_ms':round(cached_ms,2),'geographic_overlap_km2':geography['overlap_area_km2'],
        'model_version':manifest['model']['model_version'],'calibration_status':'UNCALIBRATED','confidence':None,
        'interactive_browser_result':'BLOCKED: browser URL security policy rejects localhost; no workaround used',
        'hydraulic_forecast_or_event_reconstruction':'NOT CLAIMED'}
    Path('docs/reports/implementation_04_05_qa.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return report


if __name__=='__main__':validate()
