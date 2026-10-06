"""Validate exported evidence against raster pixels and region geometry."""
import argparse
import json
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as geometry_transform
from .area import mask_area_km2
from .regions import cleaned_labels
from .threshold import candidate_mask

BASELINE = {'t1_t2': (0.0195, 1), 't1_t3': (0.7949, 30), 't2_t3': (0.0, 0)}


def require(condition,message):
    if not condition:raise ValueError(message)


def validate(directory):
    manifest=json.loads((directory/'manifest.json').read_text())
    require(manifest.get('default_pair') == 't1_t3', 'Primary comparison is not the 24-day pair')
    for pair in manifest['pairs']:
        path=directory/pair['directory']
        evidence=json.loads((path/'evidence.json').read_text())
        with rasterio.open(path/'change_raw.tif') as ds:
            change=ds.read(1);affine=ds.transform;crs=ds.crs
        with rasterio.open(path/'change_mask.tif') as ds:
            require(ds.transform==affine and ds.crs==crs,'Mask grid mismatch')
            mask=ds.read(1)
        area=mask_area_km2(mask==1,affine,crs)
        expected_area, expected_count = BASELINE[pair['id']]
        require(np.isclose(area, expected_area, rtol=0, atol=1e-10), 'Nominal baseline area changed')
        require(evidence['summary']['region_count'] == expected_count, 'Nominal baseline region count changed')
        require(np.isclose(area,evidence['summary']['changed_area_km2'],rtol=0,atol=1e-10),'Evidence area mismatch')
        require(not np.any((mask==1)&~np.isfinite(change)),'Invalid pixels classified as change')
        require(np.array_equal(mask==255,~np.isfinite(change)),'Nodata mismatch')
        method=evidence['analysis']
        regenerated=cleaned_labels(candidate_mask(change,method['threshold_db']),np.isfinite(change),
           method['cleanup']['min_region_pixels'],method['cleanup']['opening_iterations'])
        require(np.array_equal(regenerated>0,mask==1),'Saved mask not reproducible from saved change')
        regions=evidence['regions']
        require(len(regions)==evidence['summary']['region_count'],'Region count mismatch')
        require(np.isclose(sum(r['area_km2'] for r in regions),area,rtol=0,atol=1e-10),'Region area sum mismatch')
        geo=json.loads((path/'change_regions.geojson').read_text())
        require(len(geo['features'])==len(regions),'GeoJSON region count mismatch')
        project=Transformer.from_crs(4326,crs,always_xy=True).transform
        geo_area=sum(geometry_transform(project,shape(f['geometry'])).area for f in geo['features'])/1e6
        require(np.isclose(geo_area,area,rtol=.002,atol=1e-5),'Geographic vector area differs from raster area')
        for f in geo['features']:
            require(shape(f['geometry']).is_valid,'Invalid region polygon')
            require(f['properties']['validation_status']=='UNVERIFIED','Unsupported causal claim')
        with rasterio.open(path/'region_labels.tif') as ds:
            labels=ds.read(1)
            require(ds.transform==affine and ds.crs==crs,'Nominal label grid mismatch')
        with rasterio.open(path/'robust_core_mask.tif') as ds:
            core=ds.read(1)
            require(ds.transform==affine and ds.crs==crs,'Robust core grid mismatch')
        robust=json.loads((path/'robust_core.json').read_text())
        require(np.array_equal(core==255,mask==255),'Robust nodata mismatch')
        require(not np.any((core==1)&(mask!=1)),'Robust core exceeds nominal mask')
        strict=cleaned_labels(candidate_mask(change,robust['strict_threshold_db']),np.isfinite(change),
                              method['cleanup']['min_region_pixels'],method['cleanup']['opening_iterations'])
        require(np.array_equal(core==1,(strict>0)&(labels>0)),'Robust core not reproducible')
        robust_area=mask_area_km2(core==1,affine,crs)
        require(np.isclose(robust_area,robust['summary']['robust_area_km2'],rtol=0,atol=1e-10),'Robust area mismatch')
        require(np.isclose(robust_area,evidence['threshold_sensitivity']['higher_threshold']['area_km2'],rtol=0,atol=1e-10),'Strict sensitivity area mismatch')
        require(np.isclose(sum(r['robust_area_km2'] for r in robust['regions']),robust_area,rtol=0,atol=1e-10),'Robust region area sum mismatch')
        core_geo=json.loads((path/'robust_core_regions.geojson').read_text())
        core_geo_area=sum(geometry_transform(project,shape(f['geometry'])).area for f in core_geo['features'])/1e6
        require(np.isclose(core_geo_area,robust_area,rtol=.002,atol=1e-5),'Robust vector area mismatch')
        for r in robust['regions']:
            require(np.count_nonzero((labels==r['id'])&(core==1))==r['pixel_count'],'Robust region ID/pixel mismatch')
        require(all(r['validation_status']=='UNVERIFIED' for r in evidence['regions']),'Unsupported region validation upgrade')
        print(f"PASS {pair['id']}: raster, mask, region statistics and geographic polygons agree ({area:.4f} km²)")
    temporal=json.loads((directory/'temporal_consistency.json').read_text())
    tgeo=json.loads((directory/'temporal_consistency.geojson').read_text())
    original=json.loads((directory/'t1_t3/change_regions.geojson').read_text())
    require(len(temporal['regions'])==30,'Temporal region count mismatch')
    require({r['region_id'] for r in temporal['regions']}=={f['properties']['id'] for f in original['features']},'Temporal region IDs mismatch')
    require({f['properties']['id']:f['geometry'] for f in tgeo['features']}=={f['properties']['id']:f['geometry'] for f in original['features']},'Temporal geometry changed')
    require(temporal['additivity_max_abs_error_db']<=1e-4,'Temporal intervals are not additive')
    validation=json.loads((directory/'validation.json').read_text())
    vgeo=json.loads((directory/'validated_regions.geojson').read_text())
    require({f['properties']['id']:f['geometry'] for f in vgeo['features']}=={f['properties']['id']:f['geometry'] for f in original['features']},'Validation geometry changed')
    require(validation['source_screening']['reviewed_region_count']==10,'Top ten not reviewed')
    require(validation['source_screening']['region_count_with_polygon_overlap']==0,'Unexpected official extent overlap; re-review status')
    require(all(r['validation_status']=='UNVERIFIED' for r in validation['regions']),'Unsupported validation status')
    require(all(r['source_overlap_km2']==0 for r in validation['regions']),'Unexpected region overlap')
    from .validation_context import official_extent
    official_extent('data/context/unosat_20260826_flood_extent.zip')
    print('PASS extensions: temporal geometry, robust subset/areas, official-source checksum and validation status')
    print('All exported comparisons validated.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',default='data/derived/nepal_case_01')
    args=parser.parse_args();validate(Path(args.directory))


if __name__=='__main__':main()
