import json
from pathlib import Path
import numpy as np
import pytest
from src.compute.landslide_model import static_features,calculate,spatial_reference_check
from src.ingest.landslide_reference import check_url

CONFIG=json.loads(Path('config.landslide.json').read_text())


def terrain():
    return {'slope':np.array([[0,15],[30,45]],dtype='float32'),
        'roughness':np.array([[0,1],[2,3]],dtype='float32'),
        'curvature':np.array([[-3,0],[1,3]],dtype='float32'),
        'twi':np.array([[0,1],[2,3]],dtype='float32'),
        'drainage_distance':np.array([[0,100],[200,300]],dtype='float32')}


def rain(value):return {key:np.full((2,2),value,dtype='float32') for key in CONFIG['rain_reference_mm']}


def test_static_and_dynamic_contributions_reproduce_total():
    features,_=static_features(terrain(),CONFIG)
    score,contributions,weights,components=calculate(features,rain(50),np.ones((2,2),dtype='float32')*6,CONFIG)
    np.testing.assert_allclose(score,sum(contributions.values()),atol=1e-5)
    assert sum(weights.values())==pytest.approx(1)
    assert components['nisar_modifier'][0,0]==0 # Flat ground cannot acquire a slope radar modifier.
    assert components['nisar_modifier'][1,1]==100


def test_more_rain_never_reduces_attention():
    features,_=static_features(terrain(),CONFIG);previous=None
    for value in [0,10,100,1000]:
        score=calculate(features,rain(value),None,CONFIG)[0]
        if previous is not None:assert np.all(score>=previous)
        previous=score


def test_baseline_radar_is_unavailable_not_zero_evidence():
    features,_=static_features(terrain(),CONFIG)
    _,_,weights,components=calculate(features,rain(25),None,CONFIG)
    assert 'nisar_modifier' not in weights and components['nisar_modifier'] is None
    assert weights['static_terrain']==pytest.approx(.55/.9)


def test_missing_spatial_rain_or_radar_stays_missing():
    features,_=static_features(terrain(),CONFIG);raw=rain(20);raw['rain_24h'][0,0]=np.nan
    score=calculate(features,raw,np.zeros((2,2),dtype='float32'),CONFIG)[0]
    assert np.isnan(score[0,0]) and np.isfinite(score[1,1])


def test_constant_terrain_normalization_is_finite_and_explicit():
    t=terrain();t['roughness'][:]=5
    features,bounds=static_features(t,CONFIG)
    np.testing.assert_array_equal(features['roughness'],.5)
    assert bounds['roughness']==[5,5]


def test_imprecise_or_wrong_trigger_reports_cannot_create_validation():
    points=[{'row':0,'col':0,'uncertainty_m':5000},{'row':1,'col':1,'uncertainty_m':10,'trigger_matches_rain':False}]
    result=spatial_reference_check(np.ones((200,200)),points,CONFIG)
    assert result['usable_point_count']==0 and result['excluded_point_count']==2
    assert result['status']=='INSUFFICIENT_INDEPENDENT_REFERENCE'
    assert all(v is None for v in result['metrics'].values())


def test_block_review_does_not_claim_negative_labels_or_supervised_accuracy():
    score=np.tile(np.linspace(0,100,400),(400,1))
    points=[{'row':r,'col':c,'uncertainty_m':100} for r,c in [(0,200),(1,201),(110,210),(210,210),(310,310)]]
    result=spatial_reference_check(score,points,CONFIG)
    assert result['status']=='DESCRIPTIVE_SPATIAL_REFERENCE_CHECK_ONLY' and result['occupied_blocks']==4
    assert not result['random_pixel_split_used'] and not result['trained']
    assert result['metrics']['roc_auc'] is None


@pytest.mark.parametrize('url',['http://data.nasa.gov/a','https://example.com/a','https://data.nasa.gov.evil.test/a'])
def test_reference_download_hosts_are_restricted(url):
    with pytest.raises(ValueError):check_url(url)
