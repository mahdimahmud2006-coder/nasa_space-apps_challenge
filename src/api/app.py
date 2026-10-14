"""Offline-only local HTTP server for TerraPulse and its computed artifacts."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

ROOT=Path(__file__).resolve().parents[2]
WEB=ROOT/'web'
PUBLIC=WEB/'public'


class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(WEB),**kwargs)

    def translate_path(self,path):
        url=urlsplit(path).path
        if url.startswith('/cases/'):
            relative=Path(url.removeprefix('/cases/'))
            target=(PUBLIC/'cases'/relative).resolve()
            if not target.is_relative_to((PUBLIC/'cases').resolve()):
                return str(ROOT/'missing')
            return str(target)
        return super().translate_path(path)

    def do_GET(self):
        url=urlsplit(self.path).path
        if url=='/api/project':
            from src.api.readiness import readiness
            status=readiness(ROOT)
            return self.send_json(status,status=200 if status['runtime_ready'] else 503)
        if url=='/api/cases':
            cases=[]
            for path in sorted((PUBLIC/'cases').glob('*/manifest.json')):
                case=json.loads(path.read_text())
                cases.append({k:case[k] for k in ['case_id','title','status']})
            return self.send_json({'cases':cases,'offline':True})
        if url.startswith('/api/cases/'):
            parts=url.strip('/').split('/')
            if len(parts) not in (3,4):
                return self.send_error(404)
            case=parts[2]
            if not case.replace('_','').replace('-','').isalnum():
                return self.send_error(404)
            name=parts[3] if len(parts)==4 else 'manifest'
            if name in ('flood-escalation','flood-model','thermal','dna','landslide'):
                filename=name+'/manifest.json' if name in ('thermal','dna','landslide') else ('flood/model.json' if name=='flood-model' else 'flood/manifest.json')
                path=PUBLIC/'cases'/case/filename
                if not path.is_file():
                    return self.send_error(404,'Requested evidence not generated')
                return self.send_json(json.loads(path.read_text()))
            if name=='landslide-probe':
                try:
                    from src.compute.landslide_probe import probe
                    query=parse_qs(urlsplit(self.path).query)
                    data=probe(PUBLIC/'cases'/case/'landslide',query.get('observation_id',[None])[0],int(query['row'][0]),int(query['col'][0]))
                    return self.send_json(data)
                except (ValueError,KeyError):
                    return self.send_json({'error':'Invalid landslide observation or cell'},status=422)
                except (FileNotFoundError,ImportError,RuntimeError):
                    return self.send_json({'error':'Landslide outputs unavailable; run make landslide'},status=503)
            if name=='flood-probe':
                try:
                    from src.compute.flood_engine import get_engine
                    query=parse_qs(urlsplit(self.path).query)
                    engine=get_engine(ROOT,case)
                    mode=query.get('mode',['escalation'])[0]
                    if mode not in ('escalation','scenario'):raise ValueError('Unknown map mode')
                    parameters=None if mode=='escalation' else {'rainfall_multiplier':float(query.get('rainfall_multiplier',['1.5'])[0]),
                        'duration_hours':int(query.get('duration_hours',['24'])[0]),'wetness':query.get('wetness',['normal'])[0]}
                    data=engine.probe(query.get('observation_id',[engine.ids[-1]])[0],int(query['row'][0]),int(query['col'][0]),parameters)
                    return self.send_json(data)
                except (ValueError,KeyError):
                    return self.send_json({'error':'Invalid observation or map cell'},status=422)
                except (FileNotFoundError,ImportError,RuntimeError):
                    return self.send_json({'error':'Flood components unavailable; run make flood'},status=503)
            if name=='thermal-probe':
                try:
                    import rasterio
                    import math
                    query=parse_qs(urlsplit(self.path).query)
                    thermal=json.loads((PUBLIC/'cases'/case/'thermal/manifest.json').read_text())
                    scene=next(item for item in thermal['scenes'] if item['scene_id']==query['scene_id'][0])
                    row,col=int(query['row'][0]),int(query['col'][0])
                    if not 0<=row<thermal['grid']['shape'][0] or not 0<=col<thermal['grid']['shape'][1]:raise ValueError('Outside grid')
                    values={}
                    for key,filename in [('temperature_c',scene['temperature_raster']),('uncertainty_k',scene['uncertainty_raster'])]:
                        with rasterio.open(PUBLIC/'cases'/case/'thermal'/filename) as dataset:
                            value=float(dataset.read(1,window=rasterio.windows.Window(col,row,1,1))[0,0])
                            values[key]=value if math.isfinite(value) else None
                    return self.send_json({'scene_id':scene['scene_id'],'datetime':scene['datetime'],'row':row,'col':col,**values})
                except (ValueError,KeyError,StopIteration):
                    return self.send_json({'error':'Invalid thermal scene or cell'},status=422)
                except (FileNotFoundError,ImportError,RuntimeError):
                    return self.send_json({'error':'Thermal data unavailable'},status=503)
            if name=='context':
                path=PUBLIC/'cases'/case/'context/context.json'
                if not path.is_file():
                    return self.send_error(404,'Environmental context not generated; run make context')
                return self.send_json(json.loads(path.read_text()))
            temporal_aliases={'observations':'observations.json','timeline':'timeline.json','zones':'zones.geojson'}
            if name in temporal_aliases:
                path=PUBLIC/'cases'/case/'timeseries'/temporal_aliases[name]
                if not path.is_file():
                    return self.send_error(404,'Time series not generated; run make timeseries')
                return self.send_json(json.loads(path.read_text()))
            aliases={'manifest':'manifest.json','evidence':'evidence.json',
                     'regions':'change_regions.geojson','methodology':'methodology.json','metadata':'metadata.json'}
            if name not in aliases:
                return self.send_error(404)
            path=PUBLIC/'cases'/case/aliases[name]
            if not path.is_file():
                return self.send_error(404)
            return self.send_json(json.loads(path.read_text()))
        if url.startswith('/api/zones/'):
            for suffix in ('dna','similar','landslide'):
                if url.endswith('/'+suffix):
                    zone_id=url.removeprefix('/api/zones/').removesuffix('/'+suffix)
                    if not zone_id.replace('-','').isalnum():return self.send_error(404)
                    folder='landslide' if suffix=='landslide' else 'dna'
                    for path in sorted((PUBLIC/'cases').glob('*/'+folder+'/manifest.json')):
                        data=json.loads(path.read_text())
                        if suffix=='landslide':
                            rows=[r for r in data['zone_records'] if r['zone_id']==zone_id]
                            if rows:return self.send_json({'case_id':data['case_id'],'zone_id':zone_id,'model':data['model'],'validation':data['validation'],'records':rows})
                        else:
                            profile=next((r for r in data['profiles'] if r['zone_id']==zone_id),None)
                            if profile:return self.send_json(profile['similarity'] if suffix=='similar' else {'case_id':data['case_id'],'model_version':data['model_version'],**profile})
                    return self.send_error(404)
            for suffix in ('flood-escalation','flood-explanation'):
                if url.endswith('/'+suffix):
                    zone_id=url.removeprefix('/api/zones/').removesuffix('/'+suffix)
                    if not zone_id.replace('-','').isalnum():return self.send_error(404)
                    for path in sorted((PUBLIC/'cases').glob('*/flood/manifest.json')):
                        data=json.loads(path.read_text())
                        rows=[row for row in data['zone_records'] if row['zone_id']==zone_id]
                        if rows:return self.send_json({'case_id':data['case_id'],'zone_id':zone_id,'model_version':data['model']['model_version'],
                            'calibration_status':'UNCALIBRATED','records':rows})
                    return self.send_error(404)
            if url.endswith('/context'):
                zone_id=url.removeprefix('/api/zones/').removesuffix('/context')
                if not zone_id.replace('-','').isalnum():
                    return self.send_error(404)
                for path in sorted((PUBLIC/'cases').glob('*/context/context.json')):
                    context=json.loads(path.read_text())
                    rows=[row for row in context['zone_context'] if row['zone_id']==zone_id]
                    if rows:
                        return self.send_json({'case_id':context['case_id'],'zone_id':zone_id,
                                               'note':context['note'],'context':rows})
                return self.send_error(404)
            zone_id=url.removeprefix('/api/zones/')
            if not zone_id.replace('-','').isalnum():
                return self.send_error(404)
            for path in sorted((PUBLIC/'cases').glob('*/timeseries/zones.json')):
                zone=next((z for z in json.loads(path.read_text()) if z['zone_id']==zone_id),None)
                if zone:
                    rows=json.loads((path.parent/'zone_timeseries.json').read_text())
                    return self.send_json({'case_id':path.parent.parent.name,'zone':zone,
                                           'timeseries':[row for row in rows if row['zone_id']==zone_id]})
            return self.send_error(404)
        if url=='/health':
            return self.send_json({'status':'ok','offline':True})
        return super().do_GET()

    def do_POST(self):
        parts=urlsplit(self.path).path.strip('/').split('/')
        if len(parts)!=5 or parts[:2]!=['api','cases'] or parts[3:]!=['scenario','flood']:
            return self.send_error(404)
        case=parts[2]
        if not case.replace('_','').replace('-','').isalnum():return self.send_error(404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<1 or length>4096:return self.send_json({'error':'JSON request must be 1–4096 bytes'},status=413)
            payload=json.loads(self.rfile.read(length))
            from src.compute.flood_engine import get_engine
            result=get_engine(ROOT,case).scenario(payload)
            return self.send_json(result)
        except (ValueError,TypeError):
            return self.send_json({'error':'Invalid scenario. Use a known observation, multiplier 0.5–3, duration 6/12/24/48/72, and wetness dry/normal/wet/saturated. Historical sensitivity is unavailable.'},status=422)
        except (FileNotFoundError,ImportError,RuntimeError):
            return self.send_json({'error':'Flood model unavailable. Run make setup and make flood.'},status=503)

    def send_json(self,data,status=200):
        content=json.dumps(data,allow_nan=False).encode()
        self.send_response(status);self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)

    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8000)
    args=parser.parse_args()
    from src.api.readiness import readiness
    status=readiness(ROOT)
    if not status['runtime_ready']:
        parser.exit(2,'TerraPulse runtime preflight failed. Run make check-ready for missing assets/dependencies, and install requirements.txt if needed.\n')
    # Warm local scientific components once, keeping scenario requests responsive.
    if (ROOT/'data/derived/nepal_case_01/flood/manifest.json').is_file():
        try:
            from src.compute.flood_engine import get_engine
            get_engine(ROOT,'nepal_case_01')
        except (ImportError,FileNotFoundError,RuntimeError) as error:
            parser.exit(2,f'TerraPulse scientific components could not initialize: {error}\n')
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'TerraPulse · OFFLINE local assets · http://{args.host}:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()


if __name__=='__main__':main()
