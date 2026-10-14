"""Exercise HTTP request handling without binding sockets or making network requests."""
import io
import json
from types import SimpleNamespace

import pytest

from src.api import app


class LocalRequest:
    def __init__(self, path):
        self.input = io.BytesIO(f'GET {path} HTTP/1.0\r\nHost: localhost\r\n\r\n'.encode())
        self.output = bytearray()

    def makefile(self, *args, **kwargs):
        return self.input

    def sendall(self, data):
        self.output.extend(data)


def request(path):
    connection = LocalRequest(path)
    app.Handler(connection, ('127.0.0.1', 1234),
                SimpleNamespace(server_name='localhost', server_port=8000))
    header, body = bytes(connection.output).split(b'\r\n\r\n', 1)
    return int(header.split(b' ')[1]), body


@pytest.fixture
def local_public(tmp_path, monkeypatch):
    public = tmp_path / 'public'
    target = public / 'cases/nepal_case_01/timeseries'
    target.mkdir(parents=True)
    files = {'observations.json': {'case_id': 'nepal_case_01', 'observations': [{'observation_id': 'a'}]},
             'timeline.json': {'case_id': 'nepal_case_01', 'intervals': []},
             'zones.geojson': {'type': 'FeatureCollection', 'features': []},
             'zones.json': [{'zone_id': 'NP-Z123456abcdef', 'validation_status': 'UNVERIFIED'}],
             'zone_timeseries.json': [{'zone_id': 'NP-Z123456abcdef', 'timestamp': '2026-08-19T00:00:00Z'}]}
    for name, content in files.items():
        (target / name).write_text(json.dumps(content))
    monkeypatch.setattr(app, 'PUBLIC', public)
    return target


@pytest.mark.parametrize('name', ['observations', 'timeline', 'zones'])
def test_temporal_case_endpoints(local_public, name):
    status, body = request('/api/cases/nepal_case_01/' + name)
    assert status == 200
    assert isinstance(json.loads(body), dict)


def test_individual_zone_endpoint(local_public):
    status, body = request('/api/zones/NP-Z123456abcdef')
    result = json.loads(body)
    assert status == 200
    assert result['zone']['validation_status'] == 'UNVERIFIED'
    assert len(result['timeseries']) == 1


@pytest.mark.parametrize('path', ['/api/zones/missing', '/api/zones/../../secrets',
                                  '/api/cases/../timeline', '/api/cases/missing/timeline'])
def test_invalid_or_missing_temporal_paths_return_404(local_public, path):
    status, _ = request(path)
    assert status == 404


def test_context_endpoints_serve_saved_zone_date_evidence(local_public):
    target=local_public.parent/'context';target.mkdir()
    row={'zone_id':'NP-Z123456abcdef','observation_id':'a','rainfall_mm_24h':48.,'cause_status':'UNVERIFIED'}
    content={'case_id':'nepal_case_01','note':'Context supports interpretation; it does not prove cause.','zone_context':[row]}
    (target/'context.json').write_text(json.dumps(content))
    status,body=request('/api/cases/nepal_case_01/context')
    assert status==200 and json.loads(body)==content
    status,body=request('/api/zones/NP-Z123456abcdef/context')
    assert status==200 and json.loads(body)['context']==[row]
    assert json.loads(body)['note']==content['note']


@pytest.mark.parametrize('path',['/api/zones/missing/context','/api/zones/../context',
                                 '/api/cases/nepal_case_01/context'])
def test_context_not_generated_or_invalid_returns_404(local_public,path):
    status,_=request(path)
    assert status==404
