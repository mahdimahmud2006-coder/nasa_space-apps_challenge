"""Audit actual saved environmental data, grids, totals, zone metrics and APIs."""
import hashlib
import json
from pathlib import Path

from affine import Affine
import numpy as np
import pyarrow.parquet as pq
import rasterio

from src.compute.context_pipeline import project, stats
from src.compute.environment import accumulation
from src.compute.pipeline import code_hash
from src.ingest.environment import sha, safe_url


def validate(case='nepal_case_01',check_current_source=False):
    directory=Path('data/derived')/case/'context';public=Path('web/public/cases')/case/'context'
    record=json.loads((directory/'context.json').read_text())
    assert len(record['source_code_sha256'])==64
    if check_current_source:
        assert record['source_code_sha256']==code_hash(), 'Historical context source differs from current code; rebuild only when intended'
    assert record['configuration_sha256']==sha(record['configuration_file'])
    grid=record['grid'];affine=Affine(*grid['affine']);shape=tuple(grid['shape'])
    previous=directory.parent/'timeseries';old=json.loads((previous/'timeline.json').read_text())
    assert record['input_timeline_sha256']==sha(previous/'timeline.json')
    assert record['input_zone_labels_sha256']==sha(previous/'zone_labels.tif')
    assert affine==Affine(*old['canonical_grid']['affine'])*Affine.scale(3)
    assert shape==tuple(s//3 for s in old['canonical_grid']['shape'])
    sources=Path('data/context/environment')
    rain=json.loads((sources/'rainfall_sources.json').read_text())
    assert rain['source_units']=='mm/hour' and rain['bin_duration_seconds']==3600
    assert rain['native_resolution_degrees']=={'latitude':.5,'longitude':.625}
    safe_url(rain['source_url'])
    assert sha(rain['cube_file'])==rain['cube_sha256']
    terrain=record['terrain_source'];assert terrain['units']=='m' and terrain['vertical_reference']=='EGM96 geoid'
    for item in terrain['items']:
        safe_url(item['url']);assert sha(item['file'])==item['sha256']
    cube=np.load(rain['cube_file'],allow_pickle=False)
    assert len(cube['times'])==rain['time_step_count']==768
    assert np.all(np.diff(cube['times'])==3600)
    from datetime import datetime, timezone
    for item in rain['source_files']:
        safe_url(item['url']);assert sha(item['file'])==item['sha256']
        response=json.loads(Path(item['file']).read_text())
        assert response['header']['time_standard']=='UTC'
        assert response['parameters']['PRECTOTCORR']['units']=='mm/hour'
        series=response['properties']['parameter']['PRECTOTCORR']
        keys=sorted(series)
        expected_times=[int(datetime.strptime(k,'%Y%m%d%H').replace(tzinfo=timezone.utc).timestamp()) for k in keys]
        np.testing.assert_array_equal(cube['times'],expected_times)
        native=np.array([series[k] for k in keys],dtype='float32');native[native<0]=np.nan
        np.testing.assert_array_equal(cube['rates'][:,item['row'],item['col']],native)
    rejection=json.loads((sources/'imerg_rejection.json').read_text())
    assert rejection['all_imerg_downloads_excluded']
    arrays={}
    all_layers=list(record['terrain_layers'].items())
    all_layers += [(ob['observation_id']+':'+key,layer) for ob in record['observations'] for key,layer in ob['layers'].items()]
    for key,layer in all_layers:
        path=directory/layer['raster'];assert sha(path)==layer['sha256']
        with rasterio.open(path) as ds:
            assert ds.crs.to_string()==grid['crs'] and ds.transform==affine and ds.shape==shape
            assert ds.tags(ns='IMAGE_STRUCTURE').get('LAYOUT')=='COG'
            assert ds.is_tiled and ds.overviews(1) and np.isnan(ds.nodata)
            array=ds.read(1)
        arrays[key]=array
        assert np.isfinite(array).all() or key=='aspect'
        assert sha(public/path.name)==sha(path)
        assert (public/layer['preview']).is_file()
        for name,value in stats(array).items():
            assert np.isclose(value,layer['statistics'][name],rtol=1e-6),key
    assert 0<=np.nanmin(arrays['slope'])<=np.nanmax(arrays['slope'])<=90
    assert np.nanmin(arrays['roughness'])>=0 and np.nanmin(arrays['drainage_distance'])>=0
    assert np.nanmin(arrays['flow_accumulation'])>=900
    assert np.isclose(record['hydrology']['outlet_contributing_area_m2'],record['hydrology']['valid_domain_area_m2'])
    for ob in record['observations']:
        for hours in (24,72,168):
            key=f'rain_{hours}h'
            total,window=accumulation(cube['times'],cube['rates'],ob['timestamp'],hours,rain['bin_duration_seconds'])
            assert window==ob['windows'][key]
            expected=project(total,Affine(*rain['source_grid']['affine']),'EPSG:4326',shape,affine,grid['crs'])
            np.testing.assert_array_equal(expected,arrays[ob['observation_id']+':'+key])
        one=arrays[ob['observation_id']+':rain_24h'];three=arrays[ob['observation_id']+':rain_72h'];seven=arrays[ob['observation_id']+':rain_168h']
        assert np.all(one<=three+1e-5) and np.all(three<=seven+1e-5)
    with rasterio.open(previous/'zone_labels.tif') as ds:labels=ds.read(1)
    assert len(record['zone_context'])==len(old['zones'])*len(old['observations'])
    for row in record['zone_context']:
        zone=next(z for z in old['zones'] if z['zone_id']==row['zone_id'])
        rr,cc=np.where(labels==zone['id']);rr=rr//3;cc=cc//3
        for metric,key in [('elevation_m','dem'),('slope_deg','slope'),('twi','twi'),('distance_to_drainage_m','drainage_distance')]:
            assert np.isclose(row[metric],arrays[key][rr,cc].mean(),rtol=1e-6)
        for hours in (24,72,168):
            assert np.isclose(row[f'rainfall_mm_{hours}h'],arrays[row['observation_id']+f':rain_{hours}h'][rr,cc].mean(),rtol=1e-6)
        assert row['cause_status']=='UNVERIFIED'
        assert row['terrain_valid_fraction']==1 and row['rainfall_valid_fraction']==1
    assert pq.read_table(directory/'context.parquet').to_pylist()==record['zone_context']
    assert json.loads((directory/'zone_context.json').read_text())==record['zone_context']
    for path in directory.iterdir():assert sha(public/path.name)==sha(path)
    prior=json.loads(Path('docs/reports/implementation_03_prior_artifacts.json').read_text())
    for name,digest in prior.items():assert sha(name)==digest, 'Prior analytical artifact changed: '+name
    result={'status':'PASS','case_id':case,'source_code_sha256':record['source_code_sha256'],'rainfall_hourly_steps':rain['time_step_count'],'rainfall_native_cells':len(rain['source_files']),
            'terrain_tiles':len(terrain['items']),'cog_count':len(all_layers),
            'zone_date_records':len(record['zone_context']),'prior_artifacts_unchanged':len(prior),
            'grid':grid,'checks':['Source hashes, approved HTTPS hosts and native rainfall geolocation',
            'Rate-to-total conversion, complete hourly bins, no future leakage, no missing-as-zero',
            'All-pixel rainfall reproject comparison; aligned 30 m grid and true COG layout',
            'Flow area conservation and nonnegative distances',
            'Zone metrics independently sampled from saved rasters; Parquet and JSON match',
            'Public files identical and prior analytical artifacts unchanged'],
            'not_validated':['Causal attribution, rainfall accuracy against gauges, drainage against surveyed rivers',
                             'Interactive browser session and physical disconnected demo rehearsal']}
    Path('docs/reports/implementation_03_qa.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check-current-source',action='store_true')
    validate(check_current_source=parser.parse_args().check_current_source)
