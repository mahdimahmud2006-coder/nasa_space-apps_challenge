"""Deterministic, explicitly uncalibrated flood attention and counterfactual indices."""
from datetime import datetime, timezone
import hashlib
import json

import numpy as np


def validate_weights(weights):
    if not weights or any(not np.isfinite(v) or v<0 for v in weights.values()) or not np.isclose(sum(weights.values()),1):
        raise ValueError('Model weights must be nonnegative and sum to one')


def normalize_rain(values,reference):
    if not np.isfinite(reference) or reference<=0:raise ValueError('Rainfall reference must be positive')
    array=np.asarray(values,dtype='float32')
    return np.where(np.isfinite(array)&(array>=0),array/(array+reference),np.nan).astype('float32')


def fixed_normalize(array,low,high,invert=False):
    if not np.isfinite([low,high]).all() or high<low:raise ValueError('Invalid fixed normalization')
    values=np.clip((array-low)/max(high-low,1e-6),0,1)
    if high==low:values=np.where(np.isfinite(array),.5,np.nan)
    return (1-values if invert else values).astype('float32')


def weighted_score(features,weights):
    """Missing feature globally -> omit and disclose effective weights; missing cell -> nodata."""
    validate_weights(weights)
    available={key:weight for key,weight in weights.items() if features.get(key) is not None and weight>0}
    if not available:raise ValueError('No assessable score features')
    total=sum(available.values());effective={key:weight/total for key,weight in available.items()}
    shape=np.asarray(next(features[key] for key in effective)).shape
    valid=np.ones(shape,dtype=bool);score=np.zeros(shape,dtype='float32');contributions={}
    for key,weight in effective.items():
        array=np.asarray(features[key],dtype='float32')
        if array.shape!=shape:raise ValueError('Feature grids disagree')
        if np.any(np.isfinite(array)&((array<0)|(array>1))):raise ValueError('Feature outside normalized range')
        valid &= np.isfinite(array)
        component=array*(100*weight);contributions[key]=component;score+=np.nan_to_num(component)
    score[~valid]=np.nan
    for component in contributions.values():component[~valid]=np.nan
    return score,contributions,effective


def rainfall_features(times,rates,timestamp,half_life=24,multiplier=1.,duration=24):
    """Scale actual rates in the latest D complete UTC hours, never future observations.

    This is a counterfactual replay of observed rainfall, not a forecast storm.
    """
    if half_life<=0:raise ValueError('Rainfall half life must be positive')
    times=np.asarray(times,dtype='int64')
    instant=int(datetime.fromisoformat(timestamp.replace('Z','+00:00')).timestamp())
    end=instant//3600*3600;expected=np.arange(end-168*3600,end,3600)
    selection=(times>=expected[0])&(times<end)
    if not np.array_equal(times[selection],expected):raise ValueError('Incomplete or unordered hourly precipitation')
    history=np.asarray(rates[selection],dtype='float64').copy()
    history[history<0]=np.nan
    history[-duration:]*=multiplier
    complete=np.isfinite(history).all(axis=0)
    result={}
    for hours in (6,12,24,48,72,168):
        total=np.sum(history[-hours:],axis=0);total[~complete]=np.nan
        result[f'rain_{hours}h']=total.astype('float32')
    age=np.arange(167.5,-.5,-1.)
    result['rain_decay']=np.sum(history*np.exp(-np.log(2)*age[:,None,None]/half_life),axis=0).astype('float32')
    result['rain_24_72h']=np.sum(history[-72:-24],axis=0).astype('float32')
    result['rain_72_168h']=np.sum(history[:-72],axis=0).astype('float32')
    for array in result.values():array[~complete]=np.nan
    return result,{'end_utc':datetime.fromtimestamp(end,timezone.utc).isoformat().replace('+00:00','Z'),
                   'end_lag_seconds':instant-end,'bin_count':168,'duration_hours':duration,
                   'semantics':'Counterfactual: multiply only the last D complete observed hourly rates; no future rainfall is generated.'}


def scenario_parameters(request,observation_ids):
    if not isinstance(request,dict):raise ValueError('Scenario request must be a JSON object')
    allowed={'observation_id','rainfall_multiplier','duration_hours','wetness','historical_sensitivity'}
    if set(request)-allowed:raise ValueError('Unknown scenario parameter')
    identifier=request.get('observation_id',observation_ids[-1])
    if identifier not in observation_ids:raise ValueError('Unknown observation date')
    multiplier=request.get('rainfall_multiplier',1.5)
    if isinstance(multiplier,bool) or not isinstance(multiplier,(int,float)) or not np.isfinite(multiplier) or not .5<=multiplier<=3:
        raise ValueError('Rainfall multiplier must be between 0.5 and 3.0')
    duration=request.get('duration_hours',24)
    if isinstance(duration,bool) or not isinstance(duration,int) or duration not in (6,12,24,48,72):
        raise ValueError('Duration must be 6, 12, 24, 48 or 72 complete hours')
    wetness=request.get('wetness','normal')
    if wetness not in ('dry','normal','wet','saturated'):raise ValueError('Unknown antecedent wetness assumption')
    history=request.get('historical_sensitivity',False)
    if not isinstance(history,bool):raise ValueError('Historical sensitivity must be boolean')
    if history:raise ValueError('Historical sensitivity is unavailable: no labeled repeated flood cases supplied')
    return {'observation_id':identifier,'rainfall_multiplier':float(multiplier),'duration_hours':duration,
            'wetness':wetness,'historical_sensitivity':False}


def scenario_id(parameters,model_version,inputs_sha):
    encoded=json.dumps({'parameters':parameters,'model_version':model_version,'inputs_sha256':inputs_sha},sort_keys=True,separators=(',',':')).encode()
    return 'flood-'+hashlib.sha256(encoded).hexdigest()[:20]


def band(score,boundaries=(25,50,75)):
    return np.where(np.isfinite(score),np.digitize(score,boundaries),-1).astype('int8')


def area_summary(score,pixel_area_km2,baseline=None,boundaries=(25,50,75)):
    if not np.isfinite(pixel_area_km2) or pixel_area_km2<=0:raise ValueError('Invalid projected cell area')
    low_boundary,high_boundary,very_high_boundary=boundaries
    if not 0<=low_boundary<high_boundary<very_high_boundary<=100:raise ValueError('Invalid score bands')
    valid=np.isfinite(score)
    if baseline is not None:valid &= np.isfinite(baseline)
    high=valid&(score>=high_boundary);elevated=valid&(score>=low_boundary)&(score<high_boundary)
    result={'valid_area_km2':float(valid.sum()*pixel_area_km2),'coverage_fraction':float(valid.mean()),
            'elevated_area_km2':float(elevated.sum()*pixel_area_km2),'at_least_elevated_area_km2':float((valid&(score>=low_boundary)).sum()*pixel_area_km2),'high_susceptibility_area_km2':float(high.sum()*pixel_area_km2),
            'very_high_area_km2':float((valid&(score>=very_high_boundary)).sum()*pixel_area_km2),
            'mean_score':float(score[valid].astype('float64').mean()) if valid.any() else None}
    if baseline is not None:
        old=valid&(baseline>=high_boundary)
        result.update({'baseline_high_area_km2':float(old.sum()*pixel_area_km2),
            'change_from_baseline_km2':float((high.sum()-old.sum())*pixel_area_km2),
            'newly_high_area_km2':float((high&~old).sum()*pixel_area_km2),
            'no_longer_high_area_km2':float((old&~high).sum()*pixel_area_km2),
            'mean_score_change':float((score[valid]-baseline[valid]).astype('float64').mean()) if valid.any() else None})
    return result
