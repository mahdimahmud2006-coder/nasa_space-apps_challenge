"""Cloud-screened USGS Landsat surface temperature, preserving native missingness."""
from pathlib import Path
import json
import shutil

from affine import Affine
import numpy as np
from PIL import Image
import rasterio
from rasterio.warp import Resampling

from src.compute.context_pipeline import project,stats
from src.compute.flood_pipeline import colorize,json_write
from src.compute.timeseries_pipeline import cog
from src.ingest.environment import sha


def quality_mask(temperature_dn,pixel_qa,radsat,uncertainty_dn,max_uncertainty_k=3.):
    """Landsat 8/9 QA_PIXEL bits 0–5, saturation and terrain occlusion, ST_QA."""
    uncertainty=np.asarray(uncertainty_dn,dtype='float32')*.01
    valid=(temperature_dn>0)&((pixel_qa.astype('uint16')&63)==0)&(radsat==0)
    valid &=np.isfinite(uncertainty)&(uncertainty>=0)&(uncertainty<=max_uncertainty_k)
    return valid,uncertainty


def run():
    source=json.loads(Path('data/context/thermal/sources.json').read_text())
    context=json.loads(Path('data/derived/nepal_case_01/context/context.json').read_text());grid=context['grid']
    affine=Affine(*grid['affine']);shape=tuple(grid['shape']);crs=grid['crs']
    directory=Path('data/derived/nepal_case_01/thermal');directory.mkdir(exist_ok=True)
    public=Path('web/public/cases/nepal_case_01/thermal');public.mkdir(exist_ok=True)
    records=[]
    for scene in source['scenes']:
        arrays={};native=None
        for item in scene['assets']:
            if sha(item['file'])!=item['sha256']:raise ValueError('Thermal source checksum changed')
            with rasterio.open(item['file']) as ds:
                array=ds.read(1).astype('float32')
                target=project(array,ds.transform,ds.crs,shape,affine,crs,Resampling.nearest)
                arrays[item['key']]=target
        valid,uncertainty=quality_mask(arrays['lwir11'],np.nan_to_num(arrays['qa_pixel'],nan=1),
                                        arrays['qa_radsat'],arrays['qa'],max_uncertainty_k=5.)
        temp=arrays['lwir11']*.00341802+149.-273.15
        valid &=np.isfinite(temp)
        temp[~valid]=np.nan;uncertainty[~valid]=np.nan
        name=scene['scene_id']
        cog(directory/(name+'_temperature_c.tif'),temp.astype('float32'),affine,crs,'Cloud-screened Landsat land surface temperature, Celsius; native TIRS 100 m')
        cog(directory/(name+'_uncertainty_k.tif'),uncertainty.astype('float32'),affine,crs,'USGS ST_QA reported temperature uncertainty, Kelvin')
        colorize(temp,directory/(name+'_temperature.png'),'thermal',limits=(10,45))
        optical_valid=((np.nan_to_num(arrays['qa_pixel'],nan=1).astype('uint16')&63)==0)&(arrays['qa_radsat']==0)
        channels=[]
        for key in ('red','green','blue'):
            optical_valid &=(arrays[key]>0)&np.isfinite(arrays[key])
            reflectance=arrays[key]*.0000275-.2
            channels.append(np.clip(reflectance/.3,0,1)**(1/1.8))
        rgb=np.nan_to_num(np.stack(channels,axis=-1))*255
        Image.fromarray(np.concatenate([rgb,optical_valid[...,None]*255],axis=-1).astype('uint8')).save(directory/(name+'_optical.png'))
        best=None
        for row in range(0,shape[0],40):
            for col in range(0,shape[1],40):
                fraction=float(valid[row:row+40,col:col+40].mean())
                if best is None or fraction>best['valid_fraction']:
                    best={'row_start':row,'col_start':col,'height':40,'width':40,'valid_fraction':fraction}
        record={**{k:v for k,v in scene.items() if k!='assets'},'temperature_raster':name+'_temperature_c.tif',
            'uncertainty_raster':name+'_uncertainty_k.tif','preview':name+'_temperature.png','optical_preview':name+'_optical.png',
            'valid_fraction':float(valid.mean()),'strict_3k_valid_fraction':float((valid&(uncertainty<=3.)).mean()),'optical_valid_fraction':float(optical_valid.mean()),
            'statistics_celsius':stats(temp),'uncertainty_statistics_k':stats(uncertainty),
            'display_range_celsius':[10,45],
            'status':'AVAILABLE_WITH_CLOUD_GAPS' if valid.any() else 'NO_VALID_THERMAL_PIXELS',
            'assets':scene['assets'],'clear_focus_tile':best}
        records.append(record)
        print('Thermal screened:',name,'clear AOI',round(valid.mean()*100,2),'%',flush=True)
    manifest={'case_id':'nepal_case_01','grid':grid,'source':source,'scenes':records,
        'qa_rule':'Reject QA_PIXEL bits 0–5 (fill, dilated cloud, cirrus, cloud, shadow, snow), any QA_RADSAT flags, invalid DN and ST_QA uncertainty > 5 K.',
        'temperature_formula':'Celsius = DN × 0.00341802 + 149.0 − 273.15',
        'native_thermal_resolution_m':100,'analysis_grid_m':30,
        'limitations':['Land surface temperature is not air temperature and is not a direct flood predictor.',
            'Thermal acquisition dates differ from radar dates; actual times and offsets must remain visible.',
            'Cloud gaps are preserved, not filled with interpolated heat colors.',
            'ST_QA ≤ 5 K is an explicit screening choice, not a guarantee of true accuracy.',
            'TIRS native resolution is 100 m; USGS delivers a 30 m resampled grid, which does not create 30 m thermal detail.',
            'USGS documents emissivity and cloud-adjacency artifacts; temporal differences are not attributed to flooding.']}
    json_write(directory/'manifest.json',manifest)
    for path in directory.iterdir():
        if path.is_file():shutil.copy2(path,public/path.name)
    return manifest


if __name__=='__main__':run()
