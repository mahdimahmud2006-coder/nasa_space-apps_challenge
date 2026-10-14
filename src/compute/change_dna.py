"""Physical-unit temporal signatures. Observation gaps and censored recovery stay explicit."""
from datetime import datetime
import numpy as np


def instant(timestamp):
    return datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()/86400


def finite(value):
    return value is not None and np.isfinite(value)


def signature(zone, records, context, config):
    rows=sorted(records,key=lambda r:r['timestamp'])
    times=np.array([instant(r['timestamp']) for r in rows])
    if len(rows)<2 or np.any(np.diff(times)<=0):raise ValueError('DNA requires distinct ordered observations')
    magnitude=[r.get('mean_absolute_delta_from_baseline_db') for r in rows]
    valid=[i for i,m in enumerate(magnitude) if finite(m)]
    post=[i for i in valid if i>0]
    peak=max(valid,key=lambda i:magnitude[i]) if valid else None
    peak_value=float(magnitude[peak]) if peak is not None else None
    active=[i for i in post if magnitude[i]>=config['disturbance_threshold_db']]
    onset=active[0] if active else None
    previous=max((i for i in valid if i<onset),default=None) if onset is not None else None
    bracket=[rows[previous]['timestamp'],rows[onset]['timestamp']] if previous is not None else None
    # Consecutive valid endpoints only: do not silently bridge missing observations.
    growth=[(rows[i]['area_km2']-rows[i-1]['area_km2'])/(times[i]-times[i-1])
            for i in range(1,len(rows)) if finite(rows[i].get('area_km2')) and finite(rows[i-1].get('area_km2'))]
    eligible=[i for i in post if onset is not None and i>=onset]
    persistence=(sum(magnitude[i]>=config['disturbance_threshold_db'] for i in eligible)/len(eligible)) if eligible else None
    latest=magnitude[-1]
    recovery=float(np.clip(1-latest/peak_value,0,1)) if peak_value and peak_value>0 and finite(latest) else None
    half=next((i for i in valid if peak is not None and i>peak and peak_value>0 and magnitude[i]<=peak_value*.5),None)
    last_valid=valid[-1] if valid else None
    censored=bool(peak_value and half is None)
    # Recovery crossing is bracketed by observed samples, never interpolated as a precise date.
    half_bracket=None
    if half is not None:
        prev=max(i for i in valid if peak<=i<half)
        half_bracket=[float(times[prev]-times[peak]),float(times[half]-times[peak])]
    onset_context=next((r for r in context if onset is not None and r['observation_id']==rows[onset]['observation_id']),None)
    terrain=next((r for r in context if finite(r.get('slope_deg'))),None)
    features={'magnitude_db':peak_value,
        'onset_rate_db_per_day':float(magnitude[onset]/(times[onset]-times[0])) if onset is not None and finite(magnitude[0]) else None,
        'peak_growth_km2_per_day':float(max(growth)) if growth else None,
        'persistence':persistence,'recovery':recovery,
        'variability_db':float(np.std([magnitude[i] for i in post],ddof=0)) if len(post)>=2 else None,
        'peak_candidate_area_km2':max((float(r['area_km2']) for r in rows if finite(r.get('area_km2'))),default=None),
        'rain_24h_mm':onset_context.get('rainfall_mm_24h') if onset_context else None,
        'rain_72h_mm':onset_context.get('rainfall_mm_72h') if onset_context else None,
        'slope_deg':terrain.get('slope_deg') if terrain else None,
        'thermal_anomaly_c':None,'confidence':None}
    labels=[]
    if onset is not None:labels.append('Onset bracketed between radar visits')
    if peak_value is not None and peak_value>=config['disturbance_threshold_db']:labels.append(f"Baseline disturbance exceeds illustrative {config['disturbance_threshold_db']:g} dB screen")
    if persistence is not None and persistence==1:labels.append('Disturbance remains in every valid post-onset visit')
    if recovery is not None and recovery<config['recovery_label_fraction']:labels.append('Limited return toward baseline observed')
    if growth and max(growth)<0:labels.append('Successive change-mask area contracted')
    if features['slope_deg'] is not None:labels.append('Steep terrain context' if features['slope_deg']>=config['steep_context_deg'] else 'Gentle mean terrain context')
    return {'zone_id':zone['zone_id'],'features':features,'labels':labels,'observations':rows,
        'onset_bracket':bracket,'onset_bracket_days':float(times[onset]-times[previous]) if previous is not None else None,
        'peak_observation_id':rows[peak]['observation_id'] if peak is not None else None,
        'recovery_half_life_days':float(times[half]-times[peak]) if half is not None else None,
        'recovery_half_life_bracket_days':half_bracket,'recovery_half_life_censored':censored,
        'recovery_followup_days':float(times[last_valid]-times[peak]) if peak is not None and last_valid is not None else None,
        'observed_disturbance_span_days':float(times[active[-1]]-times[active[0]]) if active else None,
        'disturbance_still_observed_latest':len(rows)-1 in active,
        'persistence_denominator':len(eligible),'valid_observation_count':len(valid),'observation_count':len(rows),
        'interval_change_persistence':zone.get('persistence'),
        'data_coverage_fraction':zone.get('common_valid_fraction'),'confidence':None,'confidence_status':'UNVALIDATED',
        'thermal_status':'UNAVAILABLE: no matched spatial/temporal thermal anomaly baseline',
        'rainfall_context_timestamp':onset_context['timestamp'] if onset_context else None,
        'geometry':{'centroid_wgs84':zone.get('centroid_wgs84'),'bbox_projected':zone.get('bbox_projected')},
        'interpretation':'Descriptive retrospective radar signature, not a disaster diagnosis. Rainfall precedes first observed disturbance, not necessarily its unobserved onset.'}


def similarity(query, references, config):
    refs=[r for r in references if r['zone_id']!=query['zone_id']]
    result={'zone_id':query['zone_id'],'matches':[],'available':False,'reference_count':len(refs),
            'method':'Cosine similarity on reference-only z-standardized physical features; constant and missing dimensions excluded',
            'confidence':None,'interpretation':'Similarity describes radar behavior, not event type or independent confirmation.'}
    if len(refs)<config['minimum_similarity_references']:
        return {**result,'reason':'Insufficient independent reference zones; the current zone is not compared with itself.'}
    keys=[k for k in config['similarity_features'] if finite(query['features'].get(k)) and all(finite(r['features'].get(k)) for r in refs)]
    if not keys:return {**result,'reason':'No common observed feature dimensions'}
    matrix=np.array([[r['features'][k] for k in keys] for r in refs],dtype='float64')
    mean=matrix.mean(axis=0);std=matrix.std(axis=0);keep=std>1e-9
    keys=[k for k,yes in zip(keys,keep) if yes];matrix=matrix[:,keep];mean=mean[keep];std=std[keep]
    if len(keys)<config['minimum_similarity_dimensions']:
        return {**result,'reason':'Too few nonconstant shared dimensions for a meaningful comparison','dimensions':keys}
    q=(np.array([query['features'][k] for k in keys])-mean)/std
    if np.linalg.norm(q)<1e-12:return {**result,'reason':'Query is at the reference centroid; cosine direction is undefined','dimensions':keys}
    z=(matrix-mean)/std
    matches=[]
    for row,vector in zip(refs,z):
        if np.linalg.norm(vector)<1e-12:continue
        matches.append({'zone_id':row['zone_id'],'similarity':float(np.clip(np.dot(q,vector)/(np.linalg.norm(q)*np.linalg.norm(vector)),-1,1))})
    matches.sort(key=lambda r:(-r['similarity'],r['zone_id']))
    return {**result,'available':bool(matches),'matches':matches[:5],'reason':None if matches else 'All reference directions are undefined',
        'dimensions':keys,'reference_mean':mean.tolist(),'reference_std':std.tolist()}
