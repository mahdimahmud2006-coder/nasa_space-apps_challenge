"""Read a selected saved landslide cell, preserving missing inputs and additivity."""
import json
import math
from pathlib import Path
from affine import Affine
import rasterio
from pyproj import Transformer


def probe(directory,observation_id,row,col):
    directory=Path(directory);manifest=json.loads((directory/'manifest.json').read_text());grid=manifest['grid']
    obs=next((r for r in manifest['observations'] if r['observation_id']==(observation_id or manifest['observations'][-1]['observation_id'])),None)
    if obs is None or not 0<=row<grid['shape'][0] or not 0<=col<grid['shape'][1]:raise ValueError('Unknown observation or cell')
    def value(filename):
        if filename is None:return None
        with rasterio.open(directory/filename) as ds:x=float(ds.read(1,window=rasterio.windows.Window(col,row,1,1))[0,0])
        return x if math.isfinite(x) else None
    components={'static_terrain':value(manifest['static_raster']),'rainfall_trigger':value(obs['dynamic_raster']),'nisar_modifier':value(obs['modifier_raster'])}
    score=value(obs['total_raster']);contributions={key:components[key]*weight if score is not None else None for key,weight in obs['effective_weights'].items()}
    x,y=Affine(*grid['affine'])*(col+.5,row+.5);lon,lat=Transformer.from_crs(grid['crs'],'EPSG:4326',always_xy=True).transform(x,y)
    return {'observation_id':obs['observation_id'],'row':row,'col':col,'longitude':lon,'latitude':lat,'score':score,
        'components':components,'contributions':contributions,'effective_weights':obs['effective_weights'],
        'confidence':None,'confidence_status':'UNVALIDATED','interpretation':'Saved uncalibrated susceptibility cell, not a predicted or confirmed landslide.'}
