from datetime import datetime,timezone
import numpy as np
import pytest

from src.compute.flood_model import (normalize_rain,fixed_normalize,weighted_score,rainfall_features,
    scenario_parameters,scenario_id,area_summary,validate_weights)
from src.compute.thermal_pipeline import quality_mask


def inputs():
    end=int(datetime(2026,9,12,23,tzinfo=timezone.utc).timestamp())
    times=np.arange(end-168*3600,end+3600,3600)
    rates=np.ones((169,2,2),dtype='float32');rates[-1]=9999
    return times,rates


def test_counterfactual_only_changes_latest_selected_hours_and_never_future():
    times,rates=inputs()
    result,window=rainfall_features(times,rates,'2026-09-12T23:39:18Z',multiplier=2,duration=48)
    np.testing.assert_array_equal(result['rain_24h'],48)
    np.testing.assert_array_equal(result['rain_72h'],120)
    np.testing.assert_array_equal(result['rain_168h'],216)
    np.testing.assert_array_equal(result['rain_24_72h'],72)
    np.testing.assert_array_equal(result['rain_72_168h'],96)
    assert window['end_lag_seconds']==2358


@pytest.mark.parametrize('duration',[6,12,24,48,72])
def test_baseline_duration_independent(duration):
    times,rates=inputs()
    result,_=rainfall_features(times,rates,'2026-09-12T23:39:18Z',duration=duration)
    np.testing.assert_array_equal(result['rain_24h'],24)
    np.testing.assert_array_equal(result['rain_72h'],72)


def test_fixed_rain_normalization_preserves_multiplier_pressure():
    rain=np.array([0,10,100,1000,np.nan,-9999],dtype='float32')
    one=normalize_rain(rain,100);two=normalize_rain(rain*2,100)
    assert np.all(two[:4]>=one[:4]);assert two[2]>one[2]
    assert np.isnan(one[4:]).all()


def test_score_decomposes_and_missing_cells_are_not_zero_filled():
    features={'a':np.array([[.25,np.nan],[1.,0.]]),'b':np.full((2,2),.5)}
    score,contributions,effective=weighted_score(features,{'a':.4,'b':.6})
    assert score[0,0]==40
    assert np.isnan(score[0,1]) and all(np.isnan(c[0,1]) for c in contributions.values())
    np.testing.assert_allclose(score,contributions['a']+contributions['b'],equal_nan=True)
    assert sum(effective.values())==1


def test_unavailable_features_are_omitted_and_effective_weights_are_disclosed():
    score,components,weights=weighted_score({'a':np.ones((1,1)),'b':None},{'a':.5,'b':.5})
    assert score[0,0]==100 and weights=={'a':1} and set(components)=={'a'}


@pytest.mark.parametrize('weights',[{'a':.2},{'a':-1,'b':2},{'a':float('nan')}])
def test_invalid_weights_rejected(weights):
    with pytest.raises(ValueError):validate_weights(weights)


def test_recency_decay_values_recent_rain_more():
    times,rates=inputs();rates[:]=0;rates[0]=10
    earlier,_=rainfall_features(times,rates,'2026-09-12T23:39:18Z')
    rates[:]=0;rates[-2]=10
    later,_=rainfall_features(times,rates,'2026-09-12T23:39:18Z')
    assert (later['rain_decay']>earlier['rain_decay']).all()
    np.testing.assert_array_equal(later['rain_168h'],earlier['rain_168h'])


def test_missing_precipitation_and_missing_timestamp_fail_safely():
    times,rates=inputs();rates[0,0,0]=np.nan
    result,_=rainfall_features(times,rates,'2026-09-12T23:39:18Z')
    assert all(np.isnan(value[0,0]) for value in result.values())
    with pytest.raises(ValueError):rainfall_features(times[1:],rates[1:],'2026-09-12T23:39:18Z')


def test_area_change_conserves_added_and_removed_categories():
    baseline=np.array([[49,50],[70,np.nan]],dtype='float32')
    scenario=np.array([[60,45],[80,100]],dtype='float32')
    summary=area_summary(scenario,.0009,baseline)
    assert summary['valid_area_km2']==pytest.approx(.0027)
    assert summary['newly_high_area_km2']==pytest.approx(.0009)
    assert summary['no_longer_high_area_km2']==pytest.approx(.0009)
    assert summary['change_from_baseline_km2']==0


@pytest.mark.parametrize('payload',[{'rainfall_multiplier':True},{'rainfall_multiplier':4},{'rainfall_multiplier':float('nan')},
    {'duration_hours':7},{'duration_hours':24.0},{'wetness':'mild'},{'historical_sensitivity':True},
    {'observation_id':'future'},{'unrecognized':1},['not an object']])
def test_invalid_scenario_parameters(payload):
    with pytest.raises(ValueError):scenario_parameters(payload,['date-a'])


def test_scenario_ids_are_reproducible_and_bind_model_and_sources():
    parameters=scenario_parameters({},['date-a'])
    key=scenario_id(parameters,'v1','abc')
    assert key==scenario_id(dict(reversed(list(parameters.items()))),'v1','abc')
    assert key!=scenario_id(parameters,'v2','abc')
    assert key!=scenario_id(parameters,'v1','changed')


def test_thermal_quality_mask_rejects_cloud_shadow_fill_saturation_and_high_uncertainty():
    dn=np.full((2,4),45000,dtype='uint16');qa=np.array([[0,8,16,1],[0,0,0,0]],dtype='uint16')
    saturation=np.zeros((2,4),dtype='uint16');saturation[1,0]=1
    uncertainty=np.full((2,4),200,dtype='int16');uncertainty[1,1]=700;dn[1,2]=0
    valid,kelvin=quality_mask(dn,qa,saturation,uncertainty)
    np.testing.assert_array_equal(valid,[[True,False,False,False],[False,False,False,True]])
    assert kelvin[0,0]==2


def test_thermal_quality_threshold_is_explicit_not_implicitly_relaxed():
    args=[np.array([[45000]]),np.array([[0]]),np.array([[0]]),np.array([[450]])]
    assert not quality_mask(*args)[0][0,0]
    assert quality_mask(*args,max_uncertainty_k=5)[0][0,0]
