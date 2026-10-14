"""Cache real USGS Landsat thermal/optical subsets through Microsoft, no credentials persisted."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode,urlsplit
from urllib.request import urlopen

import numpy as np
import rasterio
from rasterio.windows import from_bounds,Window
from rasterio.warp import transform_bounds

ROOT=Path('data/context/thermal')
HOSTS={'planetarycomputer.microsoft.com','landsateuwest.blob.core.windows.net'}


def validate_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in HOSTS:raise ValueError('Unapproved thermal source host')
    return url


def read_url(url):
    validate_url(url)
    with urlopen(url,timeout=60) as response:
        validate_url(response.url);return response.read()


def run():
    ROOT.mkdir(parents=True,exist_ok=True)
    grid=json.loads(Path('data/derived/nepal_case_01/context/context.json').read_text())['grid']
    from affine import Affine
    affine=Affine(*grid['affine']);bounds=rasterio.transform.array_bounds(*grid['shape'],affine)
    catalog=ROOT/'catalog.json'
    if not catalog.exists():
        url='https://planetarycomputer.microsoft.com/api/stac/v1/search?'+urlencode({
            'collections':'landsat-c2-l2','bbox':'85.20,27.68,85.46,27.92',
            'datetime':'2026-08-01T00:00:00Z/2026-09-20T23:59:59Z','limit':100})
        catalog.write_bytes(read_url(url))
    items=json.loads(catalog.read_text())['features']
    selected=[item for item in items if item['id'].endswith('_T1') and item['properties']['datetime'][:10] in ['2026-08-18','2026-08-26','2026-09-11','2026-09-19']]
    selected.sort(key=lambda item:item['properties']['datetime'])
    if not selected:raise ValueError('No supported Landsat T1 thermal scenes in requested period')
    token=None;records=[]
    for item in selected:
        name=item['id'];dest=ROOT/name;dest.mkdir(exist_ok=True)
        (dest/'item.json').write_text(json.dumps(item,indent=2)+'\n')
        assets=[]
        for key in ['lwir11','qa','qa_pixel','qa_radsat','red','green','blue']:
            asset=item['assets'][key];url=validate_url(asset['href']);path=dest/(key+'.tif')
            if not path.exists():
                if token is None:token=json.loads(read_url('https://planetarycomputer.microsoft.com/api/sas/v1/token/landsateuwest/landsat-c2'))['token']
                print('Downloading Landsat window:',name,key,flush=True)
                # Range-read only the AOI; no global raster download or stored signed URL.
                with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR',CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.TIF',GDAL_HTTP_TIMEOUT='60'):
                    with rasterio.open(url+'?'+token) as source:
                        box=transform_bounds(grid['crs'],source.crs,*bounds,densify_pts=21)
                        floating=from_bounds(*box,transform=source.transform)
                        left=max(0,int(np.floor(floating.col_off))-1);top=max(0,int(np.floor(floating.row_off))-1)
                        right=min(source.width,int(np.ceil(floating.col_off+floating.width))+1)
                        bottom=min(source.height,int(np.ceil(floating.row_off+floating.height))+1)
                        window=Window(left,top,right-left,bottom-top)
                        array=source.read(1,window=window)
                        profile=source.profile.copy();profile.update(height=array.shape[0],width=array.shape[1],transform=source.window_transform(window),driver='GTiff',compress='deflate',tiled=True)
                        with rasterio.open(path.with_suffix('.part'),'w',**profile) as output:output.write(array,1)
                        path.with_suffix('.part').replace(path)
            with path.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            assets.append({'key':key,'file':str(path),'url':url,'sha256':digest,'metadata':asset.get('raster:bands',[])})
        records.append({'scene_id':name,'datetime':item['properties']['datetime'],
                        'platform':item['properties'].get('platform'),'scene_cloud_cover_percent':item['properties'].get('eo:cloud_cover'),
                        'geometric_tier':'T1','assets':assets,'item_file':str(dest/'item.json')})
        print('Landsat scene cached:',name,flush=True)
    manifest={'producer_organizations':['USGS','NASA'],'distributor':'Microsoft Planetary Computer (United States)',
        'collection':'landsat-c2-l2','created_utc':datetime.now(timezone.utc).isoformat(),
        'native_thermal_resolution_m':100,'delivered_grid_m':30,'scenes':records,
        'temperature_formula':'ST_C = DN * 0.00341802 + 149.0 - 273.15',
        'source_documentation':'https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature',
        'qa_documentation':'https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands'}
    (ROOT/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Thermal source cache complete:',len(records),'scenes',flush=True)


if __name__=='__main__':run()
