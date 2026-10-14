"""Download NASA POWER precipitation and Microsoft-hosted NASADEM; retain excluded IMERG diagnostics.

No Earthdata login or runtime network dependency. Never stores SAS tokens.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError

import numpy as np
import rasterio

BASE = 'https://gis.earthdata.nasa.gov/portal/rest/services/GESDISC/GPM_3IMERGHHE/ImageServer'
ROOT = Path('data/context/environment')
ALLOWED = {'gis.earthdata.nasa.gov', 'planetarycomputer.microsoft.com',
           'nasademeuwest.blob.core.windows.net', 'power.larc.nasa.gov'}


def safe_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED:
        raise ValueError('Download host is outside the approved NASA/Microsoft source list')
    return url


def download(url):
    safe_url(url)
    for attempt in range(4):
        try:
            with urlopen(url, timeout=60) as response:
                safe_url(response.url)
                return response.read()
        except (OSError, TimeoutError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save_json(path, content):
    Path(path).write_text(json.dumps(content, indent=2, allow_nan=False) + '\n')


def imerg_diagnostic(start='2026-08-12', end='2026-09-13', workers=6):
    """Exclusive end date; preserve each catalog timestamp and raw scientific TIFF."""
    raw = ROOT / 'imerg'; raw.mkdir(parents=True, exist_ok=True)
    metadata_path = ROOT / 'imerg_service.json'
    if not metadata_path.exists():
        metadata_path.write_bytes(download(BASE + '?f=pjson'))
    dates = []
    current = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
    stop = datetime.fromisoformat(end).replace(tzinfo=timezone.utc)
    while current < stop:
        dates.append(current); current += timedelta(days=1)
    records = []
    for date in dates:
        path = raw / (date.strftime('%Y%m%d') + '_catalog.json')
        where = (f"StdTime >= timestamp '{date:%Y-%m-%d} 00:00:00' AND "
                 f"StdTime < timestamp '{date + timedelta(days=1):%Y-%m-%d} 00:00:00'")
        if not path.exists():
            path.write_bytes(download(BASE + '/query?' + urlencode({
                'where': where, 'outFields': 'objectid,name,stdtime,variable',
                'returnGeometry': 'false', 'orderByFields': 'stdtime ASC',
                'resultRecordCount': 1000, 'f': 'json'})))
        catalog = json.loads(path.read_text())
        if catalog.get('error') or catalog.get('exceededTransferLimit'):
            raise ValueError(f'Incomplete NASA catalog {path}')
        entries = [f['attributes'] for f in catalog['features']]
        expected = list(range(int(date.timestamp()*1000), int((date+timedelta(days=1)).timestamp()*1000), 1800000))
        if sorted(e['stdtime'] for e in entries) != expected:
            raise ValueError(f'Missing or duplicate half-hours in {path}')
        records.extend(entries)
    print(f'NASA catalog verified: {len(records)} half-hourly records', flush=True)

    def frame(record):
        stamp = datetime.fromtimestamp(record['stdtime']/1000, timezone.utc)
        path = raw / (stamp.strftime('%Y%m%dT%H%M') + '.tif')
        if not path.exists():
            params = {'bbox': '85.2,27.6,85.5,28.0', 'bboxSR': 4326, 'imageSR': 4326,
                      'size': '3,4', 'format': 'tiff', 'pixelType': 'F32',
                      'interpolation': 'RSP_NearestNeighbor',
                      'mosaicRule': json.dumps({'mosaicMethod': 'esriMosaicLockRaster',
                                               'lockRasterIds': [record['objectid']]}),
                      'renderingRule': json.dumps({'rasterFunction': 'None'}), 'time': record['stdtime'], 'f': 'json'}
            export = json.loads(download(BASE + '/exportImage?' + urlencode(params)))
            if export.get('error'):
                raise ValueError(f'NASA export failed: {export}')
            content = download(export['href'])
            if content[:2] not in (b'II', b'MM'):
                raise ValueError(f'NASA returned non-TIFF content for {stamp}: {content[:200]}')
            part = path.with_suffix('.part'); part.write_bytes(content); part.replace(path)
        with rasterio.open(path) as dataset:
            if dataset.shape != (4, 3) or dataset.crs.to_epsg() != 4326:
                raise ValueError('Unexpected source rainfall grid')
            if not np.allclose(tuple(dataset.transform)[:6], [.1,0,85.2,0,-.1,28], atol=1e-9):
                raise ValueError('Rainfall subset is spatially shifted')
            array = dataset.read(1, masked=True).filled(np.nan).astype('float32')
        array[array < 0] = np.nan
        return record['stdtime']//1000, array, {'file': str(path), 'sha256': sha(path), **record}

    results = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = [pool.submit(frame, record) for record in records]
        for job in as_completed(jobs):
            results.append(job.result())
            if len(results) % 48 == 0:
                print(f'IMERG downloaded and checked: {len(results)}/{len(records)}', flush=True)
    results.sort(key=lambda r: r[0])
    np.savez_compressed(ROOT / 'imerg_diagnostic.npz', times=np.array([r[0] for r in results], dtype='int64'),
                        rates=np.stack([r[1] for r in results]), affine=np.array([.1,0,85.2,0,-.1,28]))
    save_json(ROOT / 'imerg_diagnostic_sources.json', {
        'dataset': 'GPM_3IMERGHHE V07 (Early Run)', 'producer_organization': 'NASA GES DISC (United States)',
        'source_url': BASE, 'doi': '10.5067/GPM/IMERG/3B-HH-E/07',
        'source_units': 'mm/hr', 'bin_duration_seconds': 1800, 'timestamp_semantics': 'start of half-hour bin, UTC',
        'start_inclusive': start, 'end_exclusive': end, 'native_resolution_degrees': .1,
        'source_grid': {'crs': 'EPSG:4326', 'shape': [4,3], 'affine': [.1,0,85.2,0,-.1,28]},
        'processing': 'Scientific F32 export, rendering None, nearest-neighbor at exact native cell centers; rates multiplied by 0.5 hours for totals.',
        'units_source': 'https://gpm.nasa.gov/data/imerg',
        'missing_values': 'Negative fill values masked; any missing bin makes that accumulation cell nodata.',
        'limitations': ['Early Run satellite estimates, not gauge-validated local measurements.',
                        'No quality/error bands supplied by this image service.',
                        'Liquid-equivalent precipitation; rainfall phase not independently verified.'],
        'cube_file': str(ROOT/'imerg_diagnostic.npz'), 'cube_sha256': sha(ROOT/'imerg_diagnostic.npz'),
        'frames': [r[2] for r in results]})
    print('Rainfall cube ready', flush=True)



def rainfall(start='20260812', end='20260912'):
    """NASA POWER PRECTOTCORR, exact native 0.5 x 0.625 degree grid centers."""
    ROOT.mkdir(parents=True,exist_ok=True)
    cells=[];values={};times=None
    for row,latitude in enumerate([28.,27.5]):
        for col,longitude in enumerate([85.,85.625]):
            url='https://power.larc.nasa.gov/api/temporal/hourly/point?'+urlencode({
                'parameters':'PRECTOTCORR','community':'AG','longitude':longitude,'latitude':latitude,
                'start':start,'end':end,'format':'JSON','time-standard':'UTC'})
            path=ROOT/f'power_{latitude}_{longitude}.json'
            if not path.exists():path.write_bytes(download(url))
            record=json.loads(path.read_text())
            if record['header']['time_standard']!='UTC':raise ValueError('POWER time standard is not UTC')
            if record['parameters']['PRECTOTCORR']['units']!='mm/hour':raise ValueError('Unexpected rainfall units')
            series=record['properties']['parameter']['PRECTOTCORR']
            keys=sorted(series)
            epochs=np.array([int(datetime.strptime(k,'%Y%m%d%H').replace(tzinfo=timezone.utc).timestamp()) for k in keys],dtype='int64')
            if times is None:times=epochs
            if not np.array_equal(epochs,times):raise ValueError('POWER cells have inconsistent time axes')
            array=np.array([series[k] for k in keys],dtype='float32')
            array[array<0]=np.nan;values[row,col]=array
            cells.append({'file':str(path),'url':url,'sha256':sha(path),'row':row,'col':col,
                          'latitude_center':latitude,'longitude_center':longitude,'header':record['header']})
            print('NASA POWER native cell saved:',latitude,longitude,flush=True)
    first=int(datetime.strptime(start,'%Y%m%d').replace(tzinfo=timezone.utc).timestamp())
    last=int((datetime.strptime(end,'%Y%m%d').replace(tzinfo=timezone.utc)+timedelta(days=1)).timestamp())
    if not np.array_equal(times,np.arange(first,last,3600,dtype='int64')):raise ValueError('Incomplete POWER hourly timeline')
    rates=np.empty((len(times),2,2),dtype='float32')
    for (row,col),array in values.items():rates[:,row,col]=array
    np.savez_compressed(ROOT/'rainfall.npz',times=times,rates=rates,affine=np.array([.625,0,84.6875,0,-.5,28.25]))
    save_json(ROOT/'rainfall_sources.json',{
        'dataset':'NASA POWER hourly PRECTOTCORR (MERRA-2 / GEOS-IT)',
        'producer_organization':'NASA Langley Research Center / NASA GMAO (United States)',
        'source_url':'https://power.larc.nasa.gov/api/temporal/hourly/point',
        'source_units':'mm/hour','bin_duration_seconds':3600,'timestamp_semantics':'UTC hourly average, labeled by hour',
        'start_inclusive':'2026-08-12','end_exclusive':'2026-09-13',
        'native_resolution_degrees':{'latitude':.5,'longitude':.625},
        'source_grid':{'crs':'EPSG:4326','shape':[2,2],'affine':[.625,0,84.6875,0,-.5,28.25]},
        'processing':'Exact native grid-center API queries; nearest-neighbor spatial placement; hourly mm/hour rates multiplied by 1 hour.',
        'units_source':'https://power.larc.nasa.gov/docs/services/api/temporal/hourly/',
        'grid_source':'https://power.larc.nasa.gov/docs/tutorials/service-data-request/api/',
        'missing_values':'Negative fill masked; any missing hour makes that accumulation cell nodata.',
        'limitations':['Coarse meteorological model/reanalysis context, not local gauge or satellite rainfall observations.',
                       'NASA API lists both MERRA2 and GEOSIT sources, without per-hour transition labels; recent data can be revised.',
                       'Native cells span roughly 50–60 km; reprojection to 30 m creates no extra precipitation detail.',
                       'Liquid-equivalent total precipitation; rainfall phase is not independently verified.'],
        'selection_reason':'IMERG GIS service exported suspicious zero-filled slices; independent getSamples for a cataloged midday slice returned a missing-resource 404. Those downloads are excluded.',
        'cube_file':str(ROOT/'rainfall.npz'),'cube_sha256':sha(ROOT/'rainfall.npz'),
        'source_files':cells,'time_step_count':len(times)})
    print('Verified NASA POWER cube ready:',rates.shape,flush=True)


def terrain():
    ROOT.mkdir(parents=True, exist_ok=True)
    collection = ROOT / 'nasadem_collection.json'
    if not collection.exists():
        collection.write_bytes(download('https://planetarycomputer.microsoft.com/api/stac/v1/collections/nasadem'))
    items = []
    for name in ['NASADEM_HGT_n27e085', 'NASADEM_HGT_n28e085']:
        url = 'https://nasademeuwest.blob.core.windows.net/nasadem-cog/v001/' + name + '.tif'
        dest = ROOT / (name + '.tif')
        if not dest.exists():
            token = json.loads(download('https://planetarycomputer.microsoft.com/api/sas/v1/token/nasademeuwest/nasadem-cog'))['token']
            part = dest.with_suffix('.part'); part.write_bytes(download(url + '?' + token)); part.replace(dest)
        with rasterio.open(dest) as ds:
            if ds.crs.to_epsg() != 4326 or ds.count != 1:
                raise ValueError('Unexpected NASADEM raster')
        items.append({'id': name, 'file': str(dest), 'url': url, 'size_bytes': dest.stat().st_size, 'sha256': sha(dest)})
        print('NASADEM verified:', name, flush=True)
    save_json(ROOT / 'terrain_sources.json', {'dataset': 'NASADEM HGT v001',
        'producer_organizations': ['NASA','JPL','USGS'], 'distributor': 'Microsoft Planetary Computer (United States)',
        'units': 'm', 'vertical_reference': 'EGM96 geoid', 'native_resolution': '1 arc-second',
        'vertical_reference_source': 'https://lpdaac.usgs.gov/documents/1273/NASADEM_User_Guide_V11.pdf', 'items': items})


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', choices=['all','rainfall','terrain','imerg-diagnostic'],default='all')
    parser.add_argument('--workers', type=int, default=6)
    args=parser.parse_args()
    if args.source in ('all','terrain'): terrain()
    if args.source in ('all','rainfall'): rainfall()

    if args.source == 'imerg-diagnostic': imerg_diagnostic(workers=args.workers)
