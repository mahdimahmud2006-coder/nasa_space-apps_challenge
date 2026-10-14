"""NASA-hosted catalog subset only; no Chinese government/agency endpoint or source report is used."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler,build_opener
from affine import Affine
from pyproj import Transformer

URL='https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv'
ALLOWED={'data.nasa.gov','data-nasa-bucket-production.s3.us-east-1.amazonaws.com'}
# Retain only independently named non-Chinese news/NGO sources, without contacting them.
REPORT_HOSTS={'thehimalayantimes.com','myrepublica.com','kathmandupost.ekantipur.com','bbc.co.uk','channelnewsasia.com','arabnews.com','reliefweb.int','outlookindia.com'}


def check_url(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.hostname not in ALLOWED:raise ValueError('Outside approved NASA catalog distribution hosts')
    return url


class ApprovedRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        check_url(newurl)
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def subset(raw,grid):
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    required={'event_id','longitude','latitude','location_accuracy','source_link','landslide_trigger'}
    if not rows or not required.issubset(rows[0]):raise ValueError('Unexpected NASA catalog schema')
    projector=Transformer.from_crs('EPSG:4326',grid['crs'],always_xy=True);inverse=~Affine(*grid['affine'])
    selected=[];points=[];source_excluded=0
    for r in rows:
        try:lon,lat=float(r['longitude']),float(r['latitude'])
        except (ValueError,TypeError):continue
        # Limit work to Nepal study geography before projecting a global catalog.
        if not 26<=lat<=31 or not 80<=lon<=89:continue
        x,y=projector.transform(lon,lat);col,row=inverse*(x,y)
        if not 0<=row<grid['shape'][0] or not 0<=col<grid['shape'][1]:continue
        host=(urlsplit(r['source_link']).hostname or '').removeprefix('www.')
        if host not in REPORT_HOSTS:source_excluded+=1;continue
        selected.append(r)
        precision=r['location_accuracy'].strip().lower()
        uncertainty=0 if precision=='exact' else float(precision[:-2])*1000 if precision.endswith('km') and precision[:-2].replace('.','').isdigit() else None
        points.append({'event_id':r['event_id'],'event_title':r['event_title'],'event_date':r['event_date'],
            'longitude':lon,'latitude':lat,'row':int(row),'col':int(col),'uncertainty_m':uncertainty,
            'location_accuracy':r['location_accuracy'],'trigger':r['landslide_trigger'],'source_name':r['source_name'],
            'source_link':r['source_link'],'nominal_point_only':True,
            'trigger_matches_rain':r['landslide_trigger'] in ('rain','downpour','continuous_rain','monsoon','tropical_cyclone','flooding')})
    return rows,selected,points,source_excluded


def run(catalog=None):
    if catalog:raw=Path(catalog).read_bytes()
    else:
        opener=build_opener(ApprovedRedirect())
        with opener.open(check_url(URL),timeout=45) as response:
            check_url(response.url);raw=response.read(20_000_001)
    if len(raw)>20_000_000:raise ValueError('Catalog exceeds bounded download')
    grid=json.loads(Path('data/derived/nepal_case_01/context/context.json').read_text())['grid']
    all_rows,rows,points,excluded=subset(raw,grid)
    directory=Path('data/context/landslide');directory.mkdir(exist_ok=True)
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(all_rows[0]));writer.writeheader();writer.writerows(rows)
    path=directory/'nasa_glc_study_subset.csv';path.write_text(stream.getvalue())
    result={'status':'NASA_CATALOG_DOWNLOADED_AND_STUDY_SUBSET_RETAINED','producer':'NASA Goddard Space Flight Center',
        'catalog_url':URL,'catalog_landing_page':'https://data.nasa.gov/dataset/global-landslide-catalog-export-f07b6',
        'full_download_sha256':hashlib.sha256(raw).hexdigest(),'full_catalog_row_count':len(all_rows),
        'subset_file':str(path),'subset_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'subset_count':len(rows),
        'source_policy_excluded_count':excluded,'report_host_allowlist':sorted(REPORT_HOSTS),'distribution_host_allowlist':sorted(ALLOWED),
        'retrieved_date_local':'2026-10-14','grid':grid,'points':points,
        'citations':['Kirschbaum et al. 2010, https://doi.org/10.1007/s11069-009-9401-4','Kirschbaum et al. 2015, https://doi.org/10.1016/j.geomorph.2015.03.016'],
        'limitations':['NASA catalog is a historical media-report compilation, not a complete or current inventory.',
            'Nominal locations with 1–50 km uncertainty cannot serve as precise 30 m labels.',
            'Only selected AOI records from the explicit non-Chinese report-host allowlist are retained. No report host was contacted.',
            'Historical earthquakes and uncertain triggers are not validation labels for the 2026 rainfall model.',
            'Unreported cells are not confirmed landslide negatives. No trained accuracy or calibration metrics are inferred.']}
    (directory/'references.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('NASA study reference records:',len(points),'source-policy exclusions:',excluded,flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--catalog',help='Optional already downloaded NASA CSV');args=parser.parse_args();run(args.catalog)
