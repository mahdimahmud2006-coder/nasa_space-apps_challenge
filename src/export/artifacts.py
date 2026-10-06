"""Local, map-ready exports. Display previews never drive measured area."""
import json
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
from PIL import Image


def write_json(path,data):
    path.write_text(json.dumps(data,indent=2,allow_nan=False))


def raster(path,array,transform,crs,nodata,description):
    with rasterio.open(path,'w',driver='GTiff',height=array.shape[0],width=array.shape[1],count=1,
       dtype=array.dtype,crs=crs,transform=transform,nodata=nodata,compress='deflate',
       tiled=True,blockxsize=256,blockysize=256) as dst:
        dst.write(array,1)
        dst.set_band_description(1,description)
        dst.update_tags(product_status='PROVISIONAL',software='TerraPulse 1.0.0')


def vectorize(labels,transform,crs,regions):
    by_id={}
    for geom,value in shapes(labels,mask=labels>0,transform=transform,connectivity=4):
        by_id.setdefault(int(value),[]).append(shape(geom))
    features=[]
    for region in regions:
        geometry=mapping(unary_union(by_id[region['id']]))
        features.append({'type':'Feature','properties':region,
                         'geometry':transform_geom(crs,'EPSG:4326',geometry,precision=7)})
    return {'type':'FeatureCollection','features':features}


def display_regions(labels):
    """Exact native pixel boundaries for local SVG hit testing."""
    return [{'id':int(value),'geometry_pixel':geom}
            for geom,value in shapes(labels,mask=labels>0,connectivity=4)]


def preview(path,array,limits,kind='radar',size=1200):
    valid=np.isfinite(array)
    if kind=='radar':
        level=np.nan_to_num(np.clip((array-limits[0])/(limits[1]-limits[0]),0,1),nan=0)
        rgb=np.stack([level*.76,level*.87,level],axis=-1)*255
    else:
        level=np.nan_to_num(np.clip(np.abs(array)/limits[1],0,1),nan=0)
        positive=array>=0
        rgb=np.empty((*array.shape,3),dtype=np.float32)
        rgb[:,:,0]=np.where(positive,240,70)*level
        rgb[:,:,1]=np.where(positive,179,160)*level
        rgb[:,:,2]=np.where(positive,55,244)*level
    rgba=np.concatenate([rgb,valid[:,:,None]*255],axis=-1).astype(np.uint8)
    im=Image.fromarray(rgba)
    im.thumbnail((size,size),Image.Resampling.LANCZOS)
    im.save(path)


def overlay(path,labels,change,size=1200):
    rgba=np.zeros((*labels.shape,4),dtype=np.uint8)
    rgba[(labels>0)&(change>=0)]=[255,199,64,230]
    rgba[(labels>0)&(change<0)]=[74,192,255,230]
    image=Image.fromarray(rgba)
    image.thumbnail((size,size),Image.Resampling.NEAREST)
    image.save(path)
