"""Transparent landslide attention, with no trained probability or confidence claims."""
import numpy as np
from src.compute.flood_model import fixed_normalize,normalize_rain,weighted_score


def static_features(terrain,config,bounds=None):
    if bounds is None:
        bounds={key:np.nanpercentile(np.abs(terrain[key]) if key=='curvature' else terrain[key],[2,98]).tolist() for key in ('roughness','curvature','twi')}
    return {'slope':np.clip(terrain['slope']/config['slope_reference_deg'],0,1).astype('float32'),
        'roughness':fixed_normalize(terrain['roughness'],*bounds['roughness']),
        'curvature_magnitude':fixed_normalize(np.abs(terrain['curvature']),*bounds['curvature']),
        'terrain_wetness':fixed_normalize(terrain['twi'],*bounds['twi']),
        'drainage_proximity':np.exp(-terrain['drainage_distance']/config['drainage_scale_m']).astype('float32')},bounds


def calculate(static,raw_rain,absolute_radar_change,config):
    terrain,_,_=weighted_score(static,config['static_weights'])
    rain={key:normalize_rain(raw_rain[key],scale) for key,scale in config['rain_reference_mm'].items()}
    trigger,_,_=weighted_score(rain,config['rain_weights'])
    modifier=None if absolute_radar_change is None else np.clip(absolute_radar_change/config['radar_absolute_change_scale_db'],0,1)*static['slope']
    features={'static_terrain':terrain/100,'rainfall_trigger':trigger/100,'nisar_modifier':modifier}
    score,contributions,effective=weighted_score(features,config['combined_weights'])
    return score,contributions,effective,{'static_terrain':terrain,'rainfall_trigger':trigger,'nisar_modifier':None if modifier is None else modifier*100}


def spatial_reference_check(score,points,config):
    """Presence-vs-background descriptive block review, never treat unreported cells as negatives.

    No fitting is performed. Independent points are deduplicated per 3 km block for
    inference; the output does not claim classification accuracy or probability calibration.
    """
    blocks={};excluded=0
    size=config['validation_block_pixels']
    for point in points:
        row,col=point['row'],point['col']
        accuracy=point.get('uncertainty_m')
        if point.get('trigger_matches_rain') is False or accuracy is None or accuracy>config['maximum_reference_uncertainty_m'] or not (0<=row<score.shape[0] and 0<=col<score.shape[1]) or not np.isfinite(score[row,col]):
            excluded+=1;continue
        blocks.setdefault((row//size,col//size),[]).append((row,col))
    count=sum(map(len,blocks.values()));background=score[np.isfinite(score)]
    result={'status':'INSUFFICIENT_INDEPENDENT_REFERENCE','usable_point_count':count,'excluded_point_count':excluded,
        'occupied_blocks':len(blocks),'block_pixels':size,'trained':False,'random_pixel_split_used':False,
        'metrics':{key:None for key in ('roc_auc','pr_auc','precision','recall','brier_score','calibration_curve')},
        'reason':'Need at least five precise independent points spanning three spatial blocks; unreported areas are not confirmed negatives.',
        'interpretation':'Historical catalog presence checks terrain association only, not 2026 rainfall triggers or forecast accuracy.'}
    if count<config['minimum_reference_points'] or len(blocks)<config['minimum_reference_blocks'] or not len(background):return result
    values=np.array([np.mean([score[r,c] for r,c in cells]) for cells in blocks.values()])
    fraction=float((background>=50).mean());observed=float((values>=50).mean())
    block_rows=[{'block_row':r,'block_col':c,'point_count':len(cells),'mean_score':float(np.mean([score[y,x] for y,x in cells]))} for (r,c),cells in sorted(blocks.items())]
    return {**result,'status':'DESCRIPTIVE_SPATIAL_REFERENCE_CHECK_ONLY','reason':'No supervised model, confirmed negatives, or event-aligned rainfall labels; empirical calibration remains unavailable.',
        'block_means':block_rows,'reference_blocks_high_fraction':observed,'aoi_high_fraction':fraction,
        'high_band_enrichment':observed/fraction if fraction>0 else None,
        'background_score_percentile':float(np.mean([np.mean(background<=value) for value in values]))}
