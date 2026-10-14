"""Export all real tracked-zone Change DNA without modifying previous time-series products."""
import json
from pathlib import Path
import shutil
import pyarrow as pa
import pyarrow.parquet as pq
from src.compute.change_dna import signature,similarity
from src.compute.flood_pipeline import json_write
from src.ingest.environment import sha


def run():
    config=json.loads(Path('config.dna.json').read_text());case=config['case_id'];base=Path('data/derived')/case
    zones=json.loads((base/'timeseries/zones.json').read_text());rows=json.loads((base/'timeseries/zone_timeseries.json').read_text())
    context=json.loads((base/'context/context.json').read_text())
    profiles=[signature(z,[r for r in rows if r['zone_id']==z['zone_id']],[r for r in context['zone_context'] if r['zone_id']==z['zone_id']],config) for z in zones]
    for profile in profiles:profile['similarity']=similarity(profile,profiles,config)
    formulas={
      'magnitude_db':'Maximum across visits of mean absolute per-pixel dB change from baseline on the same all-date common native pixels; signed means also retained',
      'onset_rate_db_per_day':'Mean absolute baseline change at first visit crossing 3 dB / elapsed days since baseline; interval average, not instantaneous speed',
      'peak_growth_km2_per_day':'Maximum successive retained change-mask area difference / elapsed days, using adjacent valid area endpoints; baseline area remains null',
      'persistence':'Visits at/after first observed 3 dB disturbance whose magnitude remains >=3 dB / valid post-onset visits; distinct from successive transition-mask persistence',
      'recovery':'1 - latest magnitude / observed peak, clipped to [0,1]; only defined with nonzero peak and valid latest sample',
      'variability_db':'Population standard deviation of valid post-baseline mean absolute changes, at least two samples',
      'recovery_half_life_days':'First sampled time at/below half the peak minus peak time; crossing bracket also exported; null/right-censored if no sampled crossing',
      'rainfall':'Complete 24/72-hour sums before first observed disturbed visit, not exact onset rainfall or causal association',
      'similarity':'Reference-only standardization, common nonconstant dimensions, no self-match; unavailable with insufficient references',
      'confidence':'Null without independent calibration. Pixel coverage and observation counts are separate quality measures'}
    manifest={'case_id':case,'model_version':config['model_version'],'status':'DESCRIPTIVE_PROVISIONAL_RADAR_BEHAVIOR',
        'config':config,'formulas':formulas,'zone_count':len(profiles),'profiles':profiles,
        'limitations':['Three radar observations cannot resolve daily onset, precise recovery half-life or long-term behavior.',
            'Zones were selected retrospectively using the full series; DNA is not a prospective alert and selection favors strong observed changes.',
            'Successive anomaly-mask contraction can coexist with persistent baseline disturbance; these measure different quantities.',
            'No disaster classes, causal rain association, empirical confidence or one-zone percentiles are fabricated.',
            'No comparable historical event library is currently available.'],
        'input_hashes':{str(p):sha(p) for p in [base/'timeseries/zones.json',base/'timeseries/zone_timeseries.json',base/'context/context.json',Path('config.dna.json'),Path('src/compute/change_dna.py'),Path('src/compute/dna_pipeline.py')]}}
    directory=base/'dna';directory.mkdir(exist_ok=True);public=Path('web/public/cases')/case/'dna';public.mkdir(exist_ok=True)
    json_write(directory/'manifest.json',manifest)
    pq.write_table(pa.Table.from_pylist([{'zone_id':p['zone_id'],**p['features']} for p in profiles]),directory/'change_dna.parquet',compression='zstd')
    for p in directory.iterdir():shutil.copy2(p,public/p.name)
    print('Change DNA exported for',len(profiles),'real tracked zones',flush=True)
    return manifest


if __name__=='__main__':run()
