import json
import pytest
from src.api import app
from test_timeseries_api import request


@pytest.fixture
def local_lab(tmp_path,monkeypatch):
    public=tmp_path/'public';case=public/'cases/nepal_case_01'
    for folder in ['dna','landslide']:(case/folder).mkdir(parents=True)
    dna={'case_id':'nepal_case_01','model_version':'dna-test','profiles':[{'zone_id':'NP-Z123','features':{'magnitude_db':7,'confidence':None},'similarity':{'zone_id':'NP-Z123','available':False,'matches':[]}}]}
    land={'case_id':'nepal_case_01','model':{'model_version':'land-test'},'validation':{'status':'UNVALIDATED'},'zone_records':[{'zone_id':'NP-Z123','score':20,'confidence':None}]}
    (case/'dna/manifest.json').write_text(json.dumps(dna));(case/'landslide/manifest.json').write_text(json.dumps(land));monkeypatch.setattr(app,'PUBLIC',public)


@pytest.mark.parametrize('path',['/api/cases/nepal_case_01/dna','/api/cases/nepal_case_01/landslide','/api/zones/NP-Z123/dna','/api/zones/NP-Z123/similar','/api/zones/NP-Z123/landslide'])
def test_new_case_and_zone_routes(local_lab,path):
    status,body=request(path);assert status==200 and isinstance(json.loads(body),dict)


def test_unavailable_similarity_stays_unavailable(local_lab):
    status,body=request('/api/zones/NP-Z123/similar');result=json.loads(body)
    assert not result['available'] and result['matches']==[]


@pytest.mark.parametrize('path',['/api/zones/NP-MISSING/dna','/api/zones/NP-MISSING/landslide','/api/zones/../similar','/api/cases/../dna'])
def test_missing_zone_or_path_traversal_rejected(local_lab,path):
    assert request(path)[0]==404


def test_probe_bad_cells_rejected(local_lab):
    status,body=request('/api/cases/nepal_case_01/landslide-probe?row=bad&col=1')
    assert status==422 and 'error' in json.loads(body)
