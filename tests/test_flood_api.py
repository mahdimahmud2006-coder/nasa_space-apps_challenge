import io
import json
from types import SimpleNamespace

import pytest
from src.api import app
from src.compute import flood_engine
from src.compute.flood_model import scenario_parameters
from test_timeseries_api import LocalRequest,request


@pytest.fixture
def local_flood(tmp_path,monkeypatch):
    public=tmp_path/'public';case=public/'cases/nepal_case_01';(case/'flood').mkdir(parents=True)
    record={'zone_id':'NP-Z123','score':42.,'contributions':{'rain_24h':22.,'terrain_wetness':20.},'confidence':None}
    manifest={'case_id':'nepal_case_01','model':{'model_version':'flood-escalation-v0.1'},'zone_records':[record]}
    (case/'flood/manifest.json').write_text(json.dumps(manifest))
    (case/'flood/model.json').write_text(json.dumps(manifest['model']))
    (case/'thermal').mkdir();(case/'thermal/manifest.json').write_text(json.dumps({'case_id':'nepal_case_01','scenes':[]}))
    monkeypatch.setattr(app,'PUBLIC',public)
    class FakeEngine:
        def scenario(self,payload):
            parameters=scenario_parameters(payload,['saved-date'])
            return {'scenario_id':'flood-test','parameters':parameters,'confidence':None}
    monkeypatch.setattr(flood_engine,'get_engine',lambda *args:FakeEngine())
    return record


def post(path,payload=None,body=None,content_length=None):
    content=json.dumps(payload).encode() if body is None else body
    if content_length is None:content_length=len(content)
    connection=LocalRequest(path)
    connection.input=io.BytesIO(f'POST {path} HTTP/1.0\r\nHost: localhost\r\nContent-Type: application/json\r\nContent-Length: {content_length}\r\n\r\n'.encode()+content)
    app.Handler(connection,('127.0.0.1',1234),SimpleNamespace(server_name='localhost',server_port=8000))
    headers,body=bytes(connection.output).split(b'\r\n\r\n',1)
    return int(headers.split(b' ')[1]),body


@pytest.mark.parametrize('endpoint',['flood-escalation','flood-model','thermal'])
def test_case_flood_and_thermal_routes(local_flood,endpoint):
    status,body=request('/api/cases/nepal_case_01/'+endpoint)
    assert status==200 and isinstance(json.loads(body),dict)


@pytest.mark.parametrize('endpoint',['flood-escalation','flood-explanation'])
def test_zone_contributions_and_confidence_are_separate(local_flood,endpoint):
    status,body=request('/api/zones/NP-Z123/'+endpoint)
    assert status==200;row=json.loads(body)['records'][0]
    assert sum(row['contributions'].values())==row['score'] and row['confidence'] is None


def test_scenario_post_serves_validated_request(local_flood):
    status,body=post('/api/cases/nepal_case_01/scenario/flood',{'rainfall_multiplier':2.,'duration_hours':48,'wetness':'wet'})
    assert status==200 and json.loads(body)['parameters']['rainfall_multiplier']==2


@pytest.mark.parametrize('payload',[{'rainfall_multiplier':4},{'duration_hours':5},{'historical_sensitivity':True},['bad']])
def test_invalid_scenario_post_returns_422(local_flood,payload):
    status,body=post('/api/cases/nepal_case_01/scenario/flood',payload)
    assert status==422 and 'error' in json.loads(body)


def test_malformed_json_and_oversized_body_are_rejected(local_flood):
    assert post('/api/cases/nepal_case_01/scenario/flood',body=b'{broken')[0]==422
    assert post('/api/cases/nepal_case_01/scenario/flood',body=b'{}',content_length=9999)[0]==413


def test_scenario_path_traversal_or_wrong_route_is_rejected(local_flood):
    assert post('/api/cases/../scenario/flood',{})[0]==404
    assert post('/api/cases/nepal_case_01/flood',{})[0]==404
