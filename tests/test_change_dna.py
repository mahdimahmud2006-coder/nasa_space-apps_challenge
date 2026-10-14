"""Meaningful formula, censoring, missing-data and cohort-leakage checks."""
import copy
import json
from pathlib import Path
import numpy as np
import pytest
from src.compute.change_dna import signature,similarity

CONFIG=json.loads(Path('config.dna.json').read_text())


def samples(magnitudes=(0,8,7),areas=(None,.02,0)):
    return [{'observation_id':str(i),'timestamp':f'2026-08-{1+i*10:02d}T00:00:00Z',
             'mean_absolute_delta_from_baseline_db':m,'area_km2':a} for i,(m,a) in enumerate(zip(magnitudes,areas))]


def make(rows):
    return signature({'zone_id':'Z','common_valid_fraction':1,'persistence':.5},rows,[],CONFIG)


def test_persistent_baseline_disturbance_is_distinct_from_mask_contraction():
    result=make(samples());f=result['features']
    assert f['magnitude_db']==8 and f['onset_rate_db_per_day']==.8
    assert f['persistence']==1 and result['interval_change_persistence']==.5
    assert f['peak_growth_km2_per_day']==pytest.approx(-.002)
    assert f['recovery']==.125 and f['variability_db']==.5
    assert result['recovery_half_life_censored'] and result['recovery_half_life_days'] is None
    assert result['recovery_followup_days']==10
    assert f['rain_24h_mm'] is None and f['thermal_anomaly_c'] is None and f['confidence'] is None


def test_half_recovery_is_sample_bracket_not_exact_crossing():
    result=make(samples((0,8,3)))
    assert result['recovery_half_life_days']==10
    assert result['recovery_half_life_bracket_days']==[0,10]
    assert not result['recovery_half_life_censored']


def test_missing_latest_never_implies_recovery_or_growth():
    result=make(samples((0,8,None),(None,.02,None)))
    assert result['features']['recovery'] is None
    assert result['features']['peak_growth_km2_per_day'] is None
    assert result['features']['variability_db'] is None
    assert result['persistence_denominator']==1


def test_missing_intermediate_observation_widens_onset_bracket():
    result=make(samples((0,None,8)))
    assert result['onset_bracket']==['2026-08-01T00:00:00Z','2026-08-21T00:00:00Z']
    assert result['onset_bracket_days']==20


def test_zero_series_does_not_create_recovery_or_onset():
    result=make(samples((0,0,0)))
    assert result['features']['recovery'] is None and result['onset_bracket'] is None
    assert not result['recovery_half_life_censored']


def test_repeated_timestamp_rejected():
    rows=samples();rows[1]['timestamp']=rows[0]['timestamp']
    with pytest.raises(ValueError):make(rows)


def test_similarity_excludes_self_and_requires_reference_cohort():
    q=make(samples());result=similarity(q,[q],CONFIG)
    assert not result['available'] and result['matches']==[] and result['reference_count']==0


def test_similarity_uses_reference_only_standardization_and_constant_dimension_removal():
    keys=CONFIG['similarity_features'];refs=[]
    for i in range(3):
        refs.append({'zone_id':str(i),'features':{key:float((i+1)*(j+1)) for j,key in enumerate(keys)}})
    for r in refs:r['features']['slope_deg']=10
    query={'zone_id':'query','features':{key:float(100*(j+1)) for j,key in enumerate(keys)}}
    query['features']['slope_deg']=20
    result=similarity(query,refs,CONFIG)
    assert result['available'] and 'slope_deg' not in result['dimensions']
    np.testing.assert_allclose(result['reference_mean'],[2*(j+1) for j in range(9)])
    assert all(-1<=r['similarity']<=1 for r in result['matches'])
    assert all(r['zone_id']!='query' for r in result['matches'])


def test_missing_similarity_dimensions_are_not_filled_with_zero():
    refs=[{'zone_id':str(i),'features':{'magnitude_db':i}} for i in range(3)]
    result=similarity({'zone_id':'Q','features':{'magnitude_db':5}},refs,CONFIG)
    assert not result['available'] and len(result['dimensions'])==1
