import copy
import json
from pathlib import Path

import numpy as np
import pytest
from affine import Affine
from src.compute.area import mask_area_km2,pixel_area_km2
from src.compute.change import delta_db,distribution
from src.compute.threshold import candidate_mask,cutoff
from src.compute.regions import cleaned_labels,region_statistics
from src.compute.uncertainty import threshold_sensitivity
from src.ingest.metadata import parse_date,build_inventory,compatibility
from src.ingest.extract_gcov import extract,analysis_window


def test_area_100_thirty_metre_pixels():
    assert mask_area_km2(np.ones((10,10),bool),Affine(30,0,0,0,-30,0),32645)==pytest.approx(.09)


def test_rotated_area_uses_determinant():
    assert pixel_area_km2(Affine(30,2,0,4,-30,0),32645)==pytest.approx(.000908)


def test_geographic_area_rejected():
    with pytest.raises(ValueError,match='Geographic'):
        pixel_area_km2(Affine(.01,0,0,0,-.01,0),4326)


def test_identical_arrays_zero_change():
    array=np.arange(9,dtype=float).reshape(3,3)
    np.testing.assert_array_equal(delta_db(array,array),np.zeros((3,3)))


def test_known_signed_delta():
    np.testing.assert_array_equal(delta_db(np.array([1.,4.]),np.array([3.,1.])),[2,-3])


def test_nodata_not_change():
    change=delta_db(np.array([np.nan,1,2,4]),np.array([1,np.inf,5,4]))
    assert np.isnan(change[:2]).all()
    assert candidate_mask(change,2).tolist()==[False,False,True,False]


def test_unaligned_arrays_rejected():
    with pytest.raises(ValueError,match='Unaligned'):
        delta_db(np.ones((3,3)),np.ones((4,3)))


def test_components_and_area():
    mask=np.zeros((12,12),bool); mask[1:3,1:3]=True; mask[5:10,5:10]=True
    labels=cleaned_labels(mask,np.ones_like(mask),10,0)
    assert np.count_nonzero(labels)==25
    result=region_statistics(labels,np.full(mask.shape,4.),Affine(30,0,300000,0,-30,3000000),32645)
    assert len(result)==1
    assert result[0]['area_km2']==pytest.approx(.0225)
    assert result[0]['median_change_db']==4


def test_cleanup_never_fills_invalid():
    mask=np.ones((10,10),bool); valid=mask.copy(); valid[4:6,4:6]=False
    labels=cleaned_labels(mask,valid,1,1)
    assert not labels[~valid].any()


def test_no_change_no_regions():
    change=np.zeros((8,8))
    labels=cleaned_labels(candidate_mask(change,1),np.isfinite(change),1,0)
    assert labels.max()==0
    assert region_statistics(labels,change,Affine(30,0,300000,0,-30,3000000),32645)==[]


def test_mad_cutoff():
    stats=distribution(np.array([-2.,-1,0,1,2]))
    assert cutoff(stats,'mad',3)==pytest.approx(3*1.4826)


def test_zero_mad_requires_explicit_threshold():
    with pytest.raises(ValueError,match='MAD is zero'):
        cutoff(distribution(np.zeros(10)),'mad',3)


@pytest.mark.parametrize('value',[0,-1,float('nan')])
def test_bad_threshold_rejected(value):
    with pytest.raises(ValueError): cutoff({'mad':1},'mad',value)


def test_sensitivity_uses_same_cleanup():
    change=np.full((10,10),4.)
    result=threshold_sensitivity(change,4,Affine(30,0,0,0,-30,0),32645,1,0)
    assert result['lower_threshold']['area_km2']==pytest.approx(.09)
    assert result['nominal']['area_km2']==pytest.approx(.09)
    assert result['higher_threshold']['area_km2']==0


def test_date_nanoseconds_and_utc():
    assert parse_date('2026-08-19T23:39:18.000000000').isoformat()=='2026-08-19T23:39:18+00:00'


@pytest.fixture
def observations():
    return build_inventory('data/derived/audit.json')['observations']


def test_same_observation_versions_not_temporal(observations):
    a=next(o for o in observations if o['filename']=='aug19.h5')
    b=next(o for o in observations if o['filename']=='aug19(1).h5')
    check=compatibility(a,b)
    assert not check['accepted']
    assert any('temporal' in reason for reason in check['reasons'])


def test_real_repeat_pair(observations):
    a=next(o for o in observations if o['filename']=='aug19.h5')
    b=next(o for o in observations if o['filename']=='aug31.h5')
    check=compatibility(a,b)
    assert check['accepted'] and check['separation_days']==12
    assert check['footprint_overlap_fraction']>.99


@pytest.mark.parametrize('key,value',[('track',1),('orbit_direction','Descending'),('product_version','other'),('spacing',[20,-20])])
def test_incompatible_geometry_rejected(observations,key,value):
    a=next(o for o in observations if o['filename']=='aug19.h5')
    b=copy.deepcopy(next(o for o in observations if o['filename']=='aug31.h5'))
    b[key]=value
    assert not compatibility(a,b)['accepted']


def test_extract_masks_and_converts_power(tmp_path):
    import h5py
    from rasterio.windows import Window
    path=tmp_path/'small.h5'
    with h5py.File(path,'w') as f:
        g=f.create_group('verified')
        d=g.create_dataset('HHHH',data=np.array([[1.,10,100],[0,-1,np.nan]],np.float32))
        d.attrs['_FillValue']=np.nan
        g.create_dataset('mask',data=[[1,0,255],[1,1,1]])
        g.create_dataset('numberOfLooks',data=np.ones((2,3)))
        g.create_dataset('xCoordinates',data=[5.,15,25])
        g.create_dataset('yCoordinates',data=[15.,5])
    ob={'grid_path':'/verified','layer_path':'/verified/HHHH','spacing':[10,-10],'covariance_term':'HHHH'}
    result,quality=extract(path,ob,Window(0,0,3,2))
    assert result[0,0]==0
    assert np.isfinite(result).sum()==1
    assert quality['valid_pixels']==1
    with h5py.File(path,'r+') as f:
        f['verified/mask'][0,:]=1
    result,_=extract(path,ob,Window(0,0,3,2))
    np.testing.assert_allclose(result[0],[0,10,20],rtol=1e-6)


def test_median_removes_isolated_speckle():
    from src.compute.preprocess import median_db
    image=np.ones((7,7),dtype=np.float32);image[3,3]=100
    filtered=median_db(image,3)
    assert filtered[3,3]==1
    assert np.isnan(filtered[0]).all()


def test_median_does_not_leak_nodata():
    from src.compute.preprocess import median_db
    image=np.ones((9,9),dtype=np.float32);image[4,4]=np.nan
    filtered=median_db(image,3)
    assert np.isnan(filtered[3:6,3:6]).all()
    assert filtered[2,2]==1


def test_histogram_zero_is_centered_and_preserves_pixel_count():
    result=distribution(np.array([-2.,0,1,8,np.nan]))['histogram']
    assert sum(result['counts'])==4
    assert result['edges_db'][40]==pytest.approx(0)
    assert result['edges_db'][0]==-result['edges_db'][-1]
