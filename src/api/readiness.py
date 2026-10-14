"""Read-only local release preflight. Does not fetch data or fabricate verification results."""
import argparse
import importlib.util
import json
from pathlib import Path


def readiness(root):
    root=Path(root);config_path=root/'config.project.json'
    project=json.loads(config_path.read_text()) if config_path.exists() else {'name':'TerraPulse','release_status':'UNCONFIGURED'}
    missing=[];invalid=[];cases=root/'web/public/cases'/project.get('case_id','nepal_case_01')
    for filename in ['index.html','studio.css','studio.mjs','terrain-view.mjs','playback.mjs','change-lab.html','change-lab.css','change-lab.mjs','timeseries.html','comparison.html']:
        if not (root/'web'/filename).is_file():missing.append('web/'+filename)
    required=['manifest.json','evidence.json','metadata.json','methodology.json','change_regions.geojson',
        'timeseries/timeline.json','timeseries/zones.json','timeseries/zone_timeseries.json','context/context.json',
        'flood/manifest.json','flood/model.json','flood/terrain_mesh.json','flood/geographic_check.json','flood/relief.png',
        'thermal/manifest.json','dna/manifest.json','dna/change_dna.parquet','landslide/manifest.json','landslide/landslide_static.png','landslide/landslide_validation.json']
    manifests={}
    for filename in required:
        path=cases/filename
        if not path.is_file():missing.append(str(path.relative_to(root)));continue
        if path.suffix=='.json':
            try:manifests[filename]=json.loads(path.read_text())
            except (ValueError,OSError):invalid.append(str(path.relative_to(root)))
    checks=[('timeseries/timeline.json','observations',['preview']),('flood/manifest.json','observations',['escalation_preview']),
        ('thermal/manifest.json','scenes',['preview','optical_preview']),('landslide/manifest.json','observations',['total_preview','dynamic_preview','total_raster','dynamic_raster'])]
    for filename,key,fields in checks:
        folder=Path(filename).parent
        for record in manifests.get(filename,{}).get(key,[]):
            for field in fields:
                value=record.get(field)
                if not isinstance(value,str) or not (cases/folder/value).is_file():missing.append(str((cases/folder/str(value)).relative_to(root)))
    derived=root/'data/derived'/project.get('case_id','nepal_case_01')/'flood'
    for name in ['manifest.json','components.npz']:
        if not (derived/name).is_file():missing.append(str((derived/name).relative_to(root)))
    # Header-only archive check keeps regular startup quick; the release CLI can hash all files separately.
    components=derived/'components.npz'
    if components.is_file():
        with components.open('rb') as stream:
            if stream.read(2)!=b'PK':invalid.append(str(components.relative_to(root)))
    packages=['numpy','scipy','rasterio','h5py','pyarrow','PIL','pyproj','shapely','affine']
    dependencies={name:importlib.util.find_spec(name) is not None for name in packages}
    ready=not missing and not invalid and all(dependencies.values())
    return {**project,'runtime_ready':ready,'missing_runtime_files':sorted(set(missing)),'invalid_runtime_files':invalid,
        'dependencies':dependencies,'acquisition_count':len(manifests.get('timeseries/timeline.json',{}).get('observations',[])),
        'tracked_zone_count':manifests.get('dna/manifest.json',{}).get('zone_count'),
        'landslide_validation_status':manifests.get('landslide/manifest.json',{}).get('validation',{}).get('status','UNAVAILABLE'),
        'capabilities':['NISAR radar comparison','Acquisition playback','Change DNA','Terrain and rainfall context','Landsat thermal/optical','Flood counterfactuals','Landslide susceptibility','Evidence export'],
        'verification_scope':'Runtime file/dependency preflight; scientific recalculation and visual QA are separate.'}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);args=parser.parse_args()
    result=readiness(args.root);print(json.dumps(result,indent=2));raise SystemExit(0 if result['runtime_ready'] else 1)


if __name__=='__main__':main()
