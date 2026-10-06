"""Windowed extraction from paths verified by the file audit."""
import hashlib
import h5py
import numpy as np
from .inspect_h5 import native
from affine import Affine
from pyproj import Transformer
from rasterio.windows import Window, from_bounds, transform as window_transform


def analysis_window(observation, center, size):
    dx,dy=observation['spacing']
    if dx <= 0 or dy >= 0:
        raise ValueError('Only north-up regular grids are supported')
    x,y=observation['origin_center']
    full=Affine(dx,0,x-dx/2,0,dy,y-dy/2)
    cx,cy=Transformer.from_crs(4326,observation['crs'],always_xy=True).transform(*center)
    w,h=size
    if w <= 0 or h <= 0 or max(w/dx,h/abs(dy)) > 6000:
        raise ValueError('AOI must be positive and at most 6000 pixels per side')
    window=from_bounds(cx-w/2,cy-h/2,cx+w/2,cy+h/2,full).round_offsets().round_lengths()
    if window.col_off < 0 or window.row_off < 0 or window.col_off+window.width > observation['shape'][1] or window.row_off+window.height > observation['shape'][0]:
        raise ValueError('AOI outside the source grid')
    return window,window_transform(window,full)


def extract(path, observation, window):
    grid=observation['grid_path']
    row,col=int(window.row_off),int(window.col_off)
    height,width=int(window.height),int(window.width)
    selection=np.s_[row:row+height,col:col+width]
    with h5py.File(path,'r') as file:
        layer=file[observation['layer_path']]
        if 'shape' in observation and list(layer.shape)!=observation['shape']:
            raise ValueError('Source layer shape changed since audit')
        if 'identification_path' in observation:
            actual_id=native(file[observation['identification_path']+'/granuleId'][()])
            if actual_id!=observation['granule_id']:
                raise ValueError('Source granule identity changed since audit')
        if layer.dtype.kind != 'f' or observation['covariance_term'][:2] != observation['covariance_term'][2:]:
            raise ValueError('dB conversion requires a real diagonal covariance power term')
        if layer.attrs.get('units', '1') not in ('1',b'1'):
            raise ValueError('Expected dimensionless power units')
        for index,(axis,spacing) in enumerate(zip(('x','y'),observation['spacing'])):
            coords=file[f'{grid}/{axis}Coordinates'][:]
            if not np.allclose(np.diff(coords),spacing,rtol=0,atol=1e-7):
                raise ValueError('Nonuniform source coordinates')
            if 'origin_center' in observation and not np.isclose(coords[0],observation['origin_center'][index],rtol=0,atol=1e-7):
                raise ValueError('Source coordinates changed since audit')
        if 'crs' in observation and observation['crs']!='EPSG:'+str(int(file[grid+'/projection'][()])):
            raise ValueError('Source CRS changed since audit')
        power=layer[selection]
        mask=file[grid+'/mask'][selection]
        looks=file[grid+'/numberOfLooks'][selection]
        valid=np.isfinite(power)&(power>0)&(mask>0)&(mask<255)&np.isfinite(looks)&(looks>0)
        for fill in [layer.attrs.get('_FillValue'), layer.fillvalue]:
            if fill is not None and np.isfinite(fill):
                valid &= power != fill
        db=np.full(power.shape,np.nan,dtype=np.float32)
        db[valid]=10*np.log10(power[valid])
        digest=hashlib.sha256(power.tobytes()+mask.tobytes()+looks.tobytes()).hexdigest()
    return db,{'window_sha256':digest,'window_sha256_content':'row-major native power, mask and numberOfLooks bytes',
               'valid_pixels':int(valid.sum()),'total_pixels':valid.size,
               'masked_pixels':int((~valid).sum()),'mask_values':np.unique(mask).tolist(),
               'positive_power_range': [float(power[valid].min()),float(power[valid].max())] if valid.any() else None}
