import copy
import numpy as np
import pytest

from src.compute.temporal_consistency import classify, augment_geojson, interval_statistics
from src.compute.robust_core import core_labels


@pytest.mark.parametrize(('final','early','late','expected'),[
    (5,2,3,'CUMULATIVE_CONSISTENT'),
    (-5,-2,-3,'CUMULATIVE_CONSISTENT'),
    (5,4.8,0.2,'EARLY_DOMINANT'),
    (-5,-0.2,-4.8,'LATE_DOMINANT'),
    (5,7,-2,'MIXED_SIGN'),
    (5,1.1,1.2,'UNSTABLE'),
])
def test_descriptive_temporal_classes(final,early,late,expected):
    assert classify(final,early,late)==expected


def test_insufficient_or_invalid_temporal_data():
    assert classify(5,2,3,0.89)=='UNSTABLE'
    assert classify(np.nan,2,3)=='UNSTABLE'
    assert classify(0,0,0)=='UNSTABLE'


def test_fraction_and_nominal_cutoff_use_same_pixels():
    result=interval_statistics(np.array([-6.,2.,5.,0.]),4)
    assert result['median_delta_db']==1
    assert result['positive_fraction']==.5
    assert result['negative_fraction']==.25
    assert result['fraction_above_nominal_cutoff']==.5


def test_region_geometry_is_unchanged():
    original={'type':'FeatureCollection','features':[{'type':'Feature','geometry':{'type':'Polygon',
       'coordinates':[[[85,27],[85.1,27],[85,27.1],[85,27]]]},'properties':{'id':7,'area_km2':.01}}]}
    baseline=copy.deepcopy(original)
    result=augment_geojson(original,[{'region_id':7,'temporal_class':'UNSTABLE','valid_fraction':.7}])
    assert result['features'][0]['geometry']==baseline['features'][0]['geometry']
    assert original==baseline
    assert result['features'][0]['properties']['area_km2']==.01


def test_robust_core_is_subset_of_nominal_labels():
    nominal=np.zeros((12,12),np.int32);nominal[2:10,2:10]=9
    change=np.ones((12,12),np.float32);change[4:8,4:8]=8
    result=core_labels(nominal,change,7,4,0)
    assert np.count_nonzero(result)==16
    assert np.all(result[result>0]==9)
    assert np.all((result>0)<=(nominal>0))


def test_robust_core_respects_cleanup_and_nodata():
    nominal=np.ones((9,9),np.int32)
    change=np.zeros((9,9),np.float32);change[4,4]=10;change[0,0]=np.nan
    result=core_labels(nominal,change,7,2,0)
    assert not result.any()
    assert result[0,0]==0
