"""Local, cached counterfactual scenario engine; no runtime external data calls."""
import json
from pathlib import Path
import shutil
from threading import RLock
from time import perf_counter

from affine import Affine
import numpy as np
import rasterio

from src.compute.context_pipeline import project
from src.compute.flood_model import normalize_rain,weighted_score,rainfall_features,area_summary,scenario_parameters,scenario_id
from src.compute.flood_pipeline import colorize,json_write,attention_tiles,LABELS
from src.compute.timeseries_pipeline import cog
from src.ingest.environment import sha


class FloodEngine:
    def __init__(self,root,case_id):
        self.root=Path(root);self.case_id=case_id
        self.directory=self.root/'data/derived'/case_id/'flood'
        self.public=self.root/'web/public/cases'/case_id/'flood'
        self.manifest=json.loads((self.directory/'manifest.json').read_text());self.config=self.manifest['model']
        if sha(self.directory/'components.npz')!=self.manifest['input_hashes']['components']:
            raise RuntimeError('Flood input checksum mismatch; rebuild components')
        with np.load(self.directory/'components.npz',allow_pickle=False) as bundle:
            self.arrays={key:bundle[key] for key in bundle.files}
        for array in self.arrays.values():array.setflags(write=False)
        self.shape=tuple(self.manifest['grid']['shape']);self.affine=Affine(*self.manifest['grid']['affine'])
        self.crs=self.manifest['grid']['crs'];self.area=self.manifest['pixel_area_km2']
        self.rain_affine=Affine(*self.manifest['rainfall_source']['source_grid']['affine'])
        self.observations=self.manifest['observations'];self.ids=[obs['observation_id'] for obs in self.observations]
        self.baselines={};self.lock=RLock()

    def features(self,parameters):
        obs=next(item for item in self.observations if item['observation_id']==parameters['observation_id'])
        native,window=rainfall_features(self.arrays['rain_times'],self.arrays['rain_rates'],obs['timestamp'],
            self.config['rain_half_life_hours'],parameters['rainfall_multiplier'],parameters['duration_hours'])
        features={'static_susceptibility':self.arrays['static_susceptibility'],
                  'wetness_assumption':np.full(self.shape,self.config['wetness_levels'][parameters['wetness']],dtype='float32')}
        for key in ('rain_24h','rain_72h'):
            rain=project(native[key],self.rain_affine,'EPSG:4326',self.shape,self.affine,self.crs)
            features[key]=normalize_rain(rain,self.config['rain_reference_mm'][key])
        for key,suffix in [('nisar_decrease','nisar'),('decrease_persistence','persistence')]:
            features[key]=self.arrays[parameters['observation_id']+'_'+suffix] if obs['radar_available'] else None
        return features,window

    def calculate(self,parameters):
        features,window=self.features(parameters)
        score,contributions,weights=weighted_score(features,self.config['scenario_weights'])
        return score,contributions,weights,window

    def baseline(self,observation_id):
        if observation_id not in self.baselines:
            params={'observation_id':observation_id,'rainfall_multiplier':1.,'duration_hours':24,'wetness':'normal','historical_sensitivity':False}
            self.baselines[observation_id]=self.calculate(params)
        return self.baselines[observation_id]

    def scenario(self,request):
        parameters=scenario_parameters(request,self.ids)
        identifier=scenario_id(parameters,self.config['model_version'],self.manifest['inputs_sha256'])
        target=self.directory/'scenarios'/identifier;cache=target/'result.json'
        with self.lock:
            if cache.is_file():return json.loads(cache.read_text())
            started=perf_counter();score,components,effective,window=self.calculate(parameters)
            baseline,base_components,base_weights,_=self.baseline(parameters['observation_id'])
            target.mkdir(parents=True,exist_ok=True)
            cog(target/'susceptibility.tif',score,self.affine,self.crs,'Uncalibrated counterfactual flood susceptibility index 0–100; not flood extent')
            delta=score-baseline
            cog(target/'delta.tif',delta,self.affine,self.crs,'Scenario minus observed-conditions susceptibility index, score points')
            colorize(score,target/'scenario.png');colorize(baseline,target/'baseline.png')
            colorize(delta,target/'delta.png','delta',(-30,30))
            valid=np.isfinite(score)&np.isfinite(baseline)
            explanation={key:float(array[valid].astype('float64').mean()) for key,array in components.items()} if valid.any() else {}
            baseline_explanation={key:float(array[valid].astype('float64').mean()) for key,array in base_components.items()} if valid.any() else {}
            url=f'/cases/{self.case_id}/flood/scenarios/{identifier}/'
            result={'case_id':self.case_id,'scenario_id':identifier,'parameters':parameters,
                'model_version':self.config['model_version'],'calibration_status':'UNCALIBRATED',
                'baseline_parameters':{'observation_id':parameters['observation_id'],'rainfall_multiplier':1.,'duration_hours':24,'wetness':'normal','historical_sensitivity':False},
                'baseline_definition':'Unmodified observed rainfall; normal wetness is assumed, not a measured soil-moisture state.',
                'interpretation':'Flood Scenario Susceptibility — a counterfactual index, not a forecast, flood extent, depth or probability.',
                'summary':area_summary(score,self.area,baseline,self.config['score_boundaries']),'effective_weights':effective,
                'contributions':explanation,'baseline_contributions':baseline_explanation,
                'contribution_labels':{key:LABELS[key] for key in explanation},
                'raster_url':url+'susceptibility.tif','delta_raster_url':url+'delta.tif',
                'preview_url':url+'scenario.png','baseline_preview_url':url+'baseline.png','delta_preview_url':url+'delta.png',
                'rainfall_window':window,'inputs_sha256':self.manifest['inputs_sha256'],
                'attention_tiles':attention_tiles(score,self.area,self.config['attention_tile_pixels'],high_threshold=self.config['score_boundaries'][1]),
                'confidence':None,'confidence_status':'UNVALIDATED','history_available':False,
                'generation_ms':round((perf_counter()-started)*1000,1)}
            json_write(cache,result)
            output=self.public/'scenarios'/identifier;output.mkdir(parents=True,exist_ok=True)
            for path in target.iterdir():shutil.copy2(path,output/path.name)
            return result

    def probe(self,observation_id,row,col,request=None):
        if observation_id not in self.ids or not 0<=row<self.shape[0] or not 0<=col<self.shape[1]:raise ValueError('Unknown observation or cell')
        if request is None:
            obs=next(item for item in self.observations if item['observation_id']==observation_id)
            features={key:self.arrays[key] for key in ('terrain_wetness','low_slope','drainage_proximity')}
            for key,reference in self.config['rain_reference_mm'].items():
                features[key]=normalize_rain(self.arrays[observation_id+'_'+key],reference)
            features['nisar_decrease']=self.arrays[observation_id+'_nisar'] if obs['radar_available'] else None
            features['decrease_persistence']=self.arrays[observation_id+'_persistence'] if obs['radar_available'] else None
            score,components,weights=weighted_score(features,self.config['escalation_weights'])
            baseline=None
        else:
            parameters=scenario_parameters({**request,'observation_id':observation_id},self.ids)
            score,components,weights,_=self.calculate(parameters)
            baseline,_,_,_=self.baseline(observation_id)
        x,y=self.affine*(col+.5,row+.5)
        from rasterio.warp import transform
        longitude,latitude=transform(self.crs,'EPSG:4326',[x],[y])
        return {'row':row,'col':col,'projected_center':[x,y],'center_wgs84':[longitude[0],latitude[0]],
            'score':float(score[row,col]) if np.isfinite(score[row,col]) else None,
            'baseline_score':float(baseline[row,col]) if baseline is not None and np.isfinite(baseline[row,col]) else None,
            'contributions':{key:float(array[row,col]) if np.isfinite(array[row,col]) else None for key,array in components.items()},
            'raw_features':{**{key:float(self.arrays[key][row,col]) if np.isfinite(self.arrays[key][row,col]) else None for key in ('elevation_m','slope_deg','twi','drainage_distance_m')},
                'observed_rain_24h_mm':float(self.arrays[observation_id+'_rain_24h'][row,col]) if np.isfinite(self.arrays[observation_id+'_rain_24h'][row,col]) else None,
                'observed_rain_72h_mm':float(self.arrays[observation_id+'_rain_72h'][row,col]) if np.isfinite(self.arrays[observation_id+'_rain_72h'][row,col]) else None},
            'effective_weights':weights,'model_version':self.config['model_version'],'confidence':None,'confidence_status':'UNVALIDATED'}


_ENGINES={};_LOCK=RLock()
def get_engine(root,case_id):
    path=Path(root)/'data/derived'/case_id/'flood/manifest.json'
    stamp=path.stat().st_mtime_ns;key=(str(root),case_id,stamp)
    with _LOCK:
        if key not in _ENGINES:
            for old in list(_ENGINES):
                if old[:2]==key[:2]:del _ENGINES[old]
            _ENGINES[key]=FloodEngine(root,case_id)
        return _ENGINES[key]
