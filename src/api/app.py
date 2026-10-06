"""Offline-only local HTTP server for TerraPulse and its computed artifacts."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

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
            aliases={'manifest':'manifest.json','evidence':'evidence.json',
                     'regions':'change_regions.geojson','methodology':'methodology.json','metadata':'metadata.json'}
            if name not in aliases:
                return self.send_error(404)
            path=PUBLIC/'cases'/case/aliases[name]
            if not path.is_file():
                return self.send_error(404)
            return self.send_json(json.loads(path.read_text()))
        if url=='/health':
            return self.send_json({'status':'ok','offline':True})
        return super().do_GET()

    def send_json(self,data):
        content=json.dumps(data,allow_nan=False).encode()
        self.send_response(200);self.send_header('Content-Type','application/json')
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
    server=ThreadingHTTPServer((args.host,args.port),Handler)
    print(f'TerraPulse · OFFLINE local assets · http://{args.host}:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: server.server_close()


if __name__=='__main__':main()
