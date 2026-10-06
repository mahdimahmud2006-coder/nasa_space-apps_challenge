"""Minimal mask cleanup and deterministic four-connected region statistics."""
import numpy as np
from scipy import ndimage
from pyproj import Transformer
from .area import pixel_area_km2


def cleaned_labels(mask,valid,min_pixels,opening_iterations=1):
    if min_pixels<1 or opening_iterations<0:
        raise ValueError('Invalid cleanup parameters')
    mask=np.asarray(mask,dtype=bool)&valid
    structure=ndimage.generate_binary_structure(2,1)
    if opening_iterations:
        mask=ndimage.binary_opening(mask,structure=structure,iterations=opening_iterations)&valid
    labels,count=ndimage.label(mask,structure)
    sizes=np.bincount(labels.ravel())
    keep=sizes>=min_pixels
    keep[0]=False
    mask=keep[labels]
    return ndimage.label(mask,structure)[0].astype(np.int32)


def region_statistics(labels,change,transform,crs):
    pixel_area=pixel_area_km2(transform,crs)
    to_wgs=Transformer.from_crs(crs,4326,always_xy=True)
    regions=[]
    for number,slc in enumerate(ndimage.find_objects(labels),1):
        if slc is None:
            continue
        selection=labels[slc]==number
        values=change[slc][selection]
        rows,cols=np.nonzero(selection)
        rows=rows+slc[0].start; cols=cols+slc[1].start
        x,y=transform @ (float(cols.mean())+.5,float(rows.mean())+.5)
        lon,lat=to_wgs.transform(x,y)
        x0,y0=transform @ (int(cols.min()),int(rows.min()))
        x1,y1=transform @ (int(cols.max())+1,int(rows.max())+1)
        regions.append({'id':number,'pixel_count':len(values),'area_km2':len(values)*pixel_area,
          'mean_change_db':float(values.mean()),'median_change_db':float(np.median(values)),
          'peak_abs_change_db':float(np.abs(values).max()),'centroid_wgs84':[lon,lat],
          'bbox_projected':[min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)],
          'interpretation':'candidate surface-change region','validation_status':'UNVERIFIED',
          'quality_flags':['Provisional product','Causal interpretation unverified','Terrain and speckle effects possible']})
    return sorted(regions,key=lambda r:(-r['area_km2'],-abs(r['median_change_db']),r['id']))
