from datetime import datetime, timezone
import numpy as np
import pytest

from src.compute.environment import accumulation, terrain_derivatives, flow_metrics
from src.ingest.environment import safe_url


def rain_input():
    end=int(datetime(2026,8,19,23,30,tzinfo=timezone.utc).timestamp())
    times=np.arange(end-168*3600,end+1800,1800,dtype='int64')
    rates=np.full((len(times),2,2),2.,dtype='float32')
    rates[-1]=1000  # Partial future bin must not leak into totals.
    return times,rates


@pytest.mark.parametrize('hours',[24,72,168])
def test_rates_integrate_to_mm_without_future_leakage(hours):
    times,rates=rain_input()
    result,window=accumulation(times,rates,'2026-08-19T23:39:18Z',hours)
    np.testing.assert_array_equal(result,np.full((2,2),hours*2))
    assert window['end_lag_seconds']==558
    assert window['bin_count']==hours*2
    assert window['end_exclusive_utc']=='2026-08-19T23:30:00Z'


def test_missing_rain_cell_never_becomes_zero():
    times,rates=rain_input();rates[-2,0,0]=np.nan;rates[-2,1,1]=-9999
    result,window=accumulation(times,rates,'2026-08-19T23:39:18Z',24)
    assert np.isnan(result[0,0]) and np.isnan(result[1,1])
    assert result[0,1]==48
    assert window['complete_cell_fraction']==.5


@pytest.mark.parametrize('kind',['missing','duplicate','reversed'])
def test_invalid_time_coverage_is_rejected(kind):
    times,rates=rain_input()
    if kind=='missing':times=np.delete(times,-2);rates=np.delete(rates,-2,axis=0)
    if kind=='duplicate':times[-2]=times[-3]
    if kind=='reversed':times=times[::-1];rates=rates[::-1]
    with pytest.raises(ValueError):accumulation(times,rates,'2026-08-19T23:39:18Z',24)


def test_plane_slope_aspect_and_curvature_units():
    yy,xx=np.mgrid[:21,:21];dem=xx.astype('float32')*30+100
    result=terrain_derivatives(dem,30,60)
    np.testing.assert_allclose(result['slope'][3:-3,3:-3],45)
    np.testing.assert_allclose(result['aspect'][3:-3,3:-3],270)
    np.testing.assert_allclose(result['curvature'][3:-3,3:-3],0)
    np.testing.assert_allclose(result['relative_elevation'][3:-3,3:-3],0,atol=1e-5)


def test_flat_terrain_has_no_aspect():
    result=terrain_derivatives(np.full((21,21),100.,dtype='float32'),30,60)
    assert np.isnan(result['aspect']).all()
    assert result['slope'][10,10]==0
    assert result['roughness'][10,10]==0


@pytest.mark.parametrize('kind',['pit','flat','plane','nodata'])
def test_hydrology_conserves_area_and_routes_without_cycles(kind):
    yy,xx=np.mgrid[:15,:15]
    dem=np.full((15,15),10.,dtype='float32')
    if kind=='pit':dem[3:12,3:12]=5;dem[7,7]=0
    if kind=='plane':dem=100-xx.astype('float32')
    if kind=='nodata':dem[5:7,5:7]=np.nan
    slope=terrain_derivatives(dem,30,30)['slope']
    layers,audit=flow_metrics(dem,30,slope,drainage_threshold_m2=9000)
    assert audit['processed_cells']==np.isfinite(dem).sum()
    assert audit['outlet_contributing_area_m2']==audit['valid_domain_area_m2']
    assert np.nanmin(layers['flow_accumulation'])>=900
    if kind=='pit':assert audit['maximum_fill_depth_m']==10
    if kind=='nodata':assert np.isnan(layers['flow_accumulation'][5,5])


@pytest.mark.parametrize('url',['http://gis.earthdata.nasa.gov/foo','https://example.cn/file',
                              'https://gis.earthdata.nasa.gov.evil.org/file','file:///etc/passwd'])
def test_dataset_host_restrictions(url):
    with pytest.raises(ValueError):safe_url(url)


def test_approved_public_nasa_microsoft_hosts():
    for host in ['gis.earthdata.nasa.gov','planetarycomputer.microsoft.com','nasademeuwest.blob.core.windows.net','power.larc.nasa.gov']:
        assert safe_url('https://'+host+'/file').startswith('https://')


def test_hourly_model_precipitation_windows_use_complete_hours():
    end=int(datetime(2026,8,19,23,tzinfo=timezone.utc).timestamp())
    times=np.arange(end-168*3600,end+3600,3600,dtype='int64')
    rates=np.ones((len(times),2,2));rates[-1]=999
    total,window=accumulation(times,rates,'2026-08-19T23:39:18Z',72,3600)
    np.testing.assert_array_equal(total,np.full((2,2),72.))
    assert window['end_lag_seconds']==2358 and window['bin_count']==72
    assert window['end_exclusive_utc']=='2026-08-19T23:00:00Z'
