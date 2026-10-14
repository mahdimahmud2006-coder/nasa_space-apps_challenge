import {TerrainView} from '/terrain-view.mjs';
import {createPlayback} from '/playback.mjs';
const $=id=>document.getElementById(id),base='/cases/nepal_case_01/',floodBase=base+'flood/',thermalBase=base+'thermal/';
const fmt=(value,digits=1)=>value===null||value===undefined?'Not assessable':Number(value).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const day=value=>new Date(value).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
const escape=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state={manifest:null,thermal:null,timeline:null,index:2,layer:'radar',scenario:null,scenarioMode:false,parameters:{rainfall_multiplier:1.5,duration_hours:48,wetness:'wet',historical_sensitivity:false},scene:null,generation:0,probe:null};
let terrain=null,player=null;
async function localJSON(path,options){const response=await fetch(path,options);if(!response.ok){let message='';try{message=(await response.json()).error||'';}catch{}throw new Error(message||`Local evidence unavailable (${response.status}). Generate it with make flood and make thermal, then restart make run.`);}return response.json();}
function error(error){player?.pause();$('studio-error').hidden=false;$('studio-error').textContent=error.message;loading(false);$('run-scenario').disabled=!state.manifest;}
function loading(value,text='Preparing saved evidence…'){$('canvas-loading').hidden=!value;$('landscape').setAttribute('aria-busy',String(value));if(value)$('canvas-loading').innerHTML='<span class="loader"></span>'+escape(text);}
const observation=()=>state.manifest.observations[state.index];
function setInspector(scenario){state.scenarioMode=scenario;if(scenario&&state.layer==='radar'){state.layer='escalation';renderMap().catch(error);}$('scenario-panel').hidden=!scenario;$('scenario-tab').classList.toggle('active',scenario);$('evidence-tab').classList.toggle('active',!scenario);$('scenario-message').textContent=state.scenario?'Showing a saved counterfactual result. Change controls, then run again.':'Counterfactual susceptibility · no forecast water depth or extent.';}
function rainChart(){
  const daily=state.manifest.rainfall_daily,width=760,height=150,left=42,bottom=30,top=24,chartWidth=width-left-5,max=Math.max(1,...daily.map(d=>d.aoi_mean_mm)),barWidth=chartWidth/daily.length;
  const date=observation().timestamp.slice(0,10),selected=daily.findIndex(item=>item.date===date);
  $('rainfall-chart').innerHTML=`<svg viewBox="0 0 ${width} ${height}" aria-label="Daily regional NASA POWER precipitation; coarse model data"><text x="0" y="20">${fmt(max,0)}</text><text x="7" y="${height-bottom}">0</text>${daily.map((item,index)=>{const h=item.aoi_mean_mm/max*(height-bottom-top);return `<rect x="${left+index*barWidth+2}" y="${height-bottom-h}" width="${Math.max(1,barWidth-4)}" height="${h}" rx="2" class="${index===selected?'active':''}"><title>${escape(item.date)}: ${fmt(item.aoi_mean_mm,2)} mm · regional model estimate</title></rect>`;}).join('')}${selected>=0?`<line class="cursor" x1="${left+(selected+.5)*barWidth}" x2="${left+(selected+.5)*barWidth}" y1="5" y2="${height-bottom}"/>`:''}${daily.filter((_,i)=>i%8===0||i===daily.length-1).map(item=>{const i=daily.indexOf(item);return `<text x="${Math.max(76,Math.min(width-38,left+(i+.5)*barWidth))}" y="${height-5}" text-anchor="middle">${escape(day(item.date+'T00:00:00Z').slice(0,6))}</text>`;}).join('')}</svg>`;
}
function contributions(values,score,scope){
  $('score-value').textContent=fmt(score,1);const thresholds=state.manifest.model.score_boundaries;
  $('score-class').textContent=score===null?'Not assessable':state.manifest.model.score_classes[thresholds.filter(t=>score>=t).length]+' index';
  $('score-scope').textContent=scope;
  const labels=state.manifest.model.feature_labels,rows=Object.entries(values).filter(([,v])=>v!==null).sort((a,b)=>b[1]-a[1]);
  $('contributions').innerHTML=rows.map(([key,value])=>`<div class="contribution-row"><div class="contribution-label"><span>${escape(labels[key]||key)}</span><strong>+${fmt(value,2)}</strong></div><div class="contribution-bar"><i style="width:${Math.max(0,Math.min(100,value/Math.max(1,...rows.map(r=>r[1]))*100))}%"></i></div></div>`).join('');
  $('contribution-note').textContent=score===null?'No index is computed where required inputs are missing.':'Unrounded contributions sum to the index. Weights and bands are uncalibrated; contributions do not establish cause.';
}
function renderEvidence(){
  const obs=observation(),scenario=state.scenario;
  $('index-title').textContent=scenario?'SCENARIO SUSCEPTIBILITY':'EXPLAINABLE FLOOD ESCALATION';
  $('metric-one-note').textContent='Index ≥ '+state.manifest.model.score_boundaries[1]+' · uncalibrated';
  $('probe-detail').hidden=!state.probe;
  if(state.probe?.raw_features){const raw=state.probe.raw_features;$('probe-detail').innerHTML=`Elevation ${fmt(raw.elevation_m,0)} m · slope ${fmt(raw.slope_deg,1)}°<br>Observed rain: ${fmt(raw.observed_rain_24h_mm,1)} mm / 24 h · ${fmt(raw.observed_rain_72h_mm,1)} mm / 72 h<br>Modeled drainage: ${fmt(raw.drainage_distance_m,0)} m · TWI ${fmt(raw.twi,1)}`;}
  if(state.probe){const p=state.probe;contributions(p.contributions,p.score,`Selected 30 m model cell · ${fmt(p.center_wgs84[1],4)}° N, ${fmt(p.center_wgs84[0],4)}° E. Rainfall remains regional.`);$('reset-probe').hidden=false;}
  else{contributions(scenario?scenario.contributions:obs.contributions,scenario?scenario.summary.mean_score:obs.summary.mean_score,scenario?'Mean scenario susceptibility over the common assessable area.':'Mean escalation index across assessable cells. Historical and thermal data are not predictors.');$('reset-probe').hidden=true;}
  const summary=scenario?scenario.summary:obs.summary;$('data-coverage').textContent=fmt(summary.coverage_fraction*100,1)+'%';
  $('metric-one-label').textContent=scenario?'SCENARIO HIGH-INDEX AREA':'AREA WITH HIGH INDEX';$('metric-one').innerHTML=fmt(summary.high_susceptibility_area_km2,2)+'<small>km²</small>';
  $('metric-two-label').textContent=scenario?'NEWLY HIGH-INDEX AREA':'ASSESSED AREA';$('metric-two').innerHTML=fmt(scenario?summary.newly_high_area_km2:summary.valid_area_km2,2)+'<small>km²</small>';
  $('metric-two-note').textContent=scenario?'Model category change; not exposure':'Missing cells excluded';
  $('metric-three-label').textContent=scenario?'CHANGE FROM BASELINE':'MEAN ATTENTION INDEX';$('metric-three').innerHTML=(scenario&&summary.mean_score_change>=0?'+':'')+fmt(scenario?summary.mean_score_change:summary.mean_score,1)+(scenario?'<small>points</small>':'<small>/ 100</small>');
  $('metric-three-note').textContent=scenario?'Same-date observed-conditions baseline':'Not a flood probability';
  const tiles=(scenario?scenario.attention_tiles:obs.attention_tiles).slice(0,5);
  $('priority-tiles').innerHTML=tiles.map((tile,index)=>`<button data-tile="${index}" aria-label="Focus analysis tile ${escape(tile.tile_id)}"><span class="rank">0${index+1}</span><span class="tile-id">${escape(tile.tile_id)}<small>${fmt(tile.high_area_km2,3)} km² with index ≥ ${state.manifest.model.score_boundaries[1]}</small></span><strong>${fmt(tile.mean_score,1)}</strong></button>`).join('');
  document.querySelectorAll('[data-tile]').forEach(button=>button.addEventListener('click',()=>{player?.pause();terrain.focus(tiles[Number(button.dataset.tile)]);}));
  if(state.layer==='radar'){
    const radar=state.timeline.observations[state.index],interval=state.timeline.intervals.find(i=>i.after===obs.observation_id),profile=state.dna?.profiles[0],sample=profile?.observations.find(r=>r.observation_id===obs.observation_id);
    $('radar-summary').textContent=`${state.timeline.observations.length} compatible radar visits · ${state.dna?.zone_count||0} tracked zones. Selected acquisition: ${day(obs.timestamp)}. Native 10 m gamma-0 HH backscatter; radar causes remain unverified.`;
    const rows=[['Selected-zone magnitude',sample?fmt(sample.mean_absolute_delta_from_baseline_db,2)+' dB':'Unavailable'],['Full-series peak',profile?fmt(profile.features.magnitude_db,2)+' dB':'Unavailable'],['Full-series disturbance persistence',profile?fmt(profile.features.persistence===null?null:profile.features.persistence*100,0)+'%':'Unavailable'],['Temporal sample',state.timeline.observations.length+' saved acquisitions']];
    $('radar-dna').innerHTML=rows.map(([label,value])=>`<dt>${escape(label)}</dt><dd>${escape(value)}</dd>`).join('');
    $('metric-one-label').textContent='SUCCESSIVE CANDIDATE AREA';$('metric-one').innerHTML=(interval?fmt(interval.candidate_area_km2,4):'Unavailable')+(interval?'<small>km²</small>':'');$('metric-one-note').textContent='Exploratory radar mask · uncalibrated cutoff';
    $('metric-two-label').textContent='RADAR GRID COVERAGE';$('metric-two').innerHTML=fmt(radar.valid_fraction*100,1)+'<small>%</small>';$('metric-two-note').textContent='Valid pixels in selected radar acquisition';
    $('metric-three-label').textContent='TRACKED-ZONE MAGNITUDE';$('metric-three').innerHTML=sample?fmt(sample.mean_absolute_delta_from_baseline_db,2)+'<small>dB</small>':'Unavailable';$('metric-three-note').textContent='Mean absolute change from baseline · first tracked zone';
  }
}
function renderThermal(probe=null){
  const scene=state.scene;if(!scene){$('thermal-detail').textContent='No independently screened thermal scene available.';return;}
  $('focus-thermal').disabled=!scene.clear_focus_tile||scene.clear_focus_tile.valid_fraction<=0;
  const offset=(new Date(scene.datetime)-new Date(observation().timestamp))/86400000;
  const label=Math.abs(offset)<1?`${fmt(Math.abs(offset)*24,1)} hours`:`${fmt(Math.abs(offset),1)} days`;
  const temperature=probe?probe.temperature_c:scene.statistics_celsius.mean;
  const temperatureText=temperature===null?'No retrieval':fmt(temperature,1)+'°C';
  $('thermal-detail').innerHTML=`<div>${escape(day(scene.datetime))} · ${escape(scene.platform||'Landsat')}<br><span class="quality-note">${label} ${offset>0?'after':'before'} selected radar acquisition</span></div><div class="thermal-stats"><div><strong>${temperatureText}</strong><small>${probe?'Selected cell':'Mean of valid thermal pixels'}</small></div><div><strong>${fmt(scene.valid_fraction*100,1)}%</strong><small>Cloud / quality screened AOI</small></div></div><div class="quality-note">Reported retrieval uncertainty: ${fmt(probe?probe.uncertainty_k:scene.uncertainty_statistics_k.mean,1)} K${probe&&probe.temperature_c===null?' · No valid thermal retrieval at this cell':''}</div><div>Native TIRS: 100 m · delivered at 30 m</div>`;
}
function legend(kind){
  const entries={escalation:['Uncalibrated attention index','0','50','100','Model bands, not probability.'],radar:['HH radar backscatter','Low','Shared contrast','High','Gamma-0 dB preview; not a flood mask.'],thermal:['Land surface temperature','10°C','27.5°C','45°C','Cloud / quality gaps appear hatched.'],optical:['Landsat optical context','Visible','','RGB','Cloud / quality gaps preserve missingness.'],terrain:['NASADEM relief','Low','','High','Historical terrain; display shading only.'],delta:['Scenario minus baseline','−30','0','+30','Index points, not water depth.']};
  const key=state.scenario&&state.layer==='escalation'?'escalation':kind,item=entries[key];
  $('legend-title').textContent=state.scenario&&kind==='escalation'?'Scenario susceptibility index':item[0];$('legend-low').textContent=item[1];$('legend-mid').textContent=item[2];$('legend-high').textContent=item[3];$('legend-note').textContent=item[4];
  $('legend-ramp').className='legend-ramp '+(key==='thermal'?'thermal':key==='delta'?'delta':key==='radar'?'radar':key==='terrain'||key==='optical'?'terrain':'');
}
async function renderMap(){
  if(!terrain)return;const token=++state.generation;loading(true);
  const obs=observation(),scenario=state.scenario;let layer=floodBase+obs.escalation_preview,before=layer,caption='Explainable escalation index · illustrative weights and thresholds, not a calibrated flood forecast.';
  terrain.opacity=.83;terrain.split=1;
  if(state.layer==='radar'){const radar=state.timeline.observations.find(o=>o.observation_id===obs.observation_id);layer=base+'timeseries/'+radar.preview;before=layer;terrain.opacity=.94;caption='NISAR HH gamma-0 backscatter · PROVISIONAL · a radar observation, not a flood classification.';}
  if(state.layer==='thermal'||state.layer==='optical'){
    if(!state.scene)throw new Error('No screened Landsat observation is available');
    layer=thermalBase+(state.layer==='thermal'?state.scene.preview:state.scene.optical_preview);before=layer;terrain.opacity=.95;
    caption=state.layer==='thermal'?'USGS Landsat land surface temperature · cloud/QA screened, reported uncertainty ≤ 5 K. Thermal date is independent of radar.':'USGS Landsat surface reflectance · visible RGB context with cloud/QA gaps. Actual optical acquisition date shown.';
  }
  if(state.layer==='terrain'){layer=floodBase+'relief.png';before=layer;terrain.opacity=0;caption='NASADEM historical elevation · true height mesh with display exaggeration. Modeled drainage is not surveyed river geometry.';}
  if(state.layer==='delta'&&scenario){layer=scenario.delta_preview_url;before=layer;terrain.opacity=.91;caption='Difference between counterfactual and same-date baseline susceptibility indices. This is not a map of future inundation.';}
  if(state.layer==='escalation'&&scenario){layer=scenario.preview_url;before=scenario.baseline_preview_url;terrain.split=Number($('compare-slider').value)/100;caption=`Applied ${fmt(scenario.parameters.rainfall_multiplier,2)}× over prior ${scenario.parameters.duration_hours} h · ${scenario.parameters.wetness} wetness. Left: unmodified rain, normal wetness assumed. Right: counterfactual.`;}
  await terrain.setImages(floodBase+'relief.png',layer,before);if(token!==state.generation)return;
  $('compare-control').hidden=!(scenario&&state.layer==='escalation');
  $('map-date').textContent=(state.layer==='thermal'||state.layer==='optical')?day(state.scene.datetime)+' · LANDSAT':day(obs.timestamp)+' · NISAR';
  $('layer-caption').textContent=caption;$('coverage-badge').textContent=state.layer==='thermal'?fmt(state.scene.valid_fraction*100,1)+'% thermal':state.layer==='optical'?fmt(state.scene.optical_valid_fraction*100,1)+'% optical':fmt(obs.summary.coverage_fraction*100,1)+'% assessed';
  document.querySelectorAll('[data-layer]').forEach(button=>{button.classList.toggle('active',button.dataset.layer===state.layer);button.setAttribute('aria-pressed',String(button.dataset.layer===state.layer));});
  document.querySelectorAll('[data-date]').forEach(button=>{const selected=Number(button.dataset.date)===state.index;button.classList.toggle('active',selected);if(selected)button.setAttribute('aria-current','date');else button.removeAttribute('aria-current');});
  $('radar-panel').hidden=state.layer!=='radar';$('evidence-panel').hidden=state.layer==='radar';$('priority-panel').hidden=state.layer==='radar';
  legend(state.layer);renderEvidence();renderThermal();rainChart();loading(false);
}
async function selectObservation(index){
  state.index=index;state.probe=null;state.scenario=null;if(state.layer==='delta')state.layer='escalation';
  $('clear-scenario').hidden=true;document.querySelector('[data-layer="delta"]').disabled=true;
  const available=state.thermal.scenes.filter(scene=>scene.valid_fraction>0);
  state.scene=available.sort((a,b)=>Math.abs(new Date(a.datetime)-new Date(observation().timestamp))-Math.abs(new Date(b.datetime)-new Date(observation().timestamp)))[0]||null;
  if(state.scene)$('thermal-scene').value=state.scene.scene_id;
  $('scenario-message').textContent='Selected date changed. Run a new counterfactual for these observed conditions.';
  await renderMap();
}
async function runScenario(){
  player?.pause();state.probe=null;const obs=observation(),token=++state.generation;
  $('run-scenario').disabled=true;$('scenario-message').textContent='Computing the weighted counterfactual from local component rasters…';loading(true,'Computing the counterfactual…');
  try{
    const result=await localJSON('/api/cases/nepal_case_01/scenario/flood',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...state.parameters,observation_id:obs.observation_id})});
    if(token!==state.generation)return;
    state.scenario=result;state.layer='escalation';$('clear-scenario').hidden=false;document.querySelector('[data-layer="delta"]').disabled=false;
    await renderMap();if(state.scenario!==result)return;$('scenario-message').textContent=`${result.scenario_id} · generated in ${fmt(result.generation_ms/1000,2)} s · ${fmt(result.summary.newly_high_area_km2,2)} km² newly in the high-index band. No population exposure is implied.`;
  }catch(cause){error(cause);}finally{$('run-scenario').disabled=false;}
}
async function inspectCell(point){
  player?.pause();const token=state.generation;
  try{
    const query=new URLSearchParams({observation_id:observation().observation_id,row:point.row,col:point.col,mode:state.scenario?'scenario':'escalation'});
    if(state.scenario)for(const key of ['rainfall_multiplier','duration_hours','wetness'])query.set(key,state.scenario.parameters[key]);
    const probe=await localJSON('/api/cases/nepal_case_01/flood-probe?'+query);if(token!==state.generation)return;state.probe=probe;renderEvidence();
    if(state.layer==='thermal'&&state.scene){const thermal=await localJSON('/api/cases/nepal_case_01/thermal-probe?'+new URLSearchParams({scene_id:state.scene.scene_id,row:point.row,col:point.col}));if(token===state.generation)renderThermal(thermal);}
  }catch(cause){error(cause);}
}
function renderGeography(data){
  const rings=geometry=>geometry.type==='Polygon'?geometry.coordinates:geometry.coordinates.flatMap(polygon=>polygon);
  const study=rings(data.study_geometry_projected),mapped=rings(data.mapped_geometry_projected),points=[...study,...mapped].flat();
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]),lowX=Math.min(...xs),highX=Math.max(...xs),lowY=Math.min(...ys),highY=Math.max(...ys);
  const scale=Math.min(600/(highX-lowX),265/(highY-lowY)),x=value=>50+(value-lowX)*scale,y=value=>295-(value-lowY)*scale;
  const path=parts=>parts.map(ring=>'M'+ring.map(p=>x(p[0])+','+y(p[1])).join('L')+'Z').join('');
  $('geography-map').innerHTML=`<svg viewBox="0 0 700 330" role="img" aria-label="Study AOI outline and independent UNOSAT mapped impact footprints"><path d="${path(mapped)}" fill="#efaa7c80" stroke="#f4ae83" stroke-width="1"/><path d="${path(study)}" fill="#7ad9c415" stroke="#7ad9c4" stroke-width="2"/><text x="30" y="25" fill="#7ad9c4" font-size="16">Cyan: current study AOI</text><text x="30" y="48" fill="#f4ae83" font-size="16">Coral: UNOSAT mudflow/rockflow mapping</text><text x="640" y="55" fill="#bacdd4" font-size="16">N ↑</text></svg>`;
  $('geography-detail').innerHTML=`<p>Intersection with available independent mapping: <strong>${fmt(data.overlap_area_km2,3)} km²</strong>. Closest mapped footprint is approximately ${fmt(data.closest_mapped_distance_km,2)} km from the study boundary. Display polygons are simplified; intersection uses the original archived geometry.</p><p>${escape(data.interpretation)}</p><p>${escape(data.model_scope)}</p><p><a href="${escape(data.source_url)}" target="_blank" rel="noreferrer">UNOSAT / UNESCO source ↗</a> · <a href="${escape(data.event_mechanism_source)}" target="_blank" rel="noreferrer">WHO event context ↗</a></p>`;
}
function buildSources(){
  const m=state.manifest.model;
  $('sources-content').innerHTML=`<h3>Measured observations and independent context</h3><p>NISAR L2 GCOV PROVISIONAL: ${state.manifest.observations.length} compatible acquisitions; each map is a saved observation. NASADEM: historical elevation from NASA/JPL/USGS. NASA POWER: hourly regional model/reanalysis precipitation at 0.5° latitude × 0.625° longitude. USGS Landsat 8/9: real surface temperature and optical data, distributed through Microsoft Planetary Computer.</p><p><a href="https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature" target="_blank" rel="noreferrer">USGS thermal methods ↗</a> · <a href="https://power.larc.nasa.gov/docs/services/api/temporal/hourly/" target="_blank" rel="noreferrer">NASA POWER hourly data ↗</a></p><h3>Model ${escape(m.model_version)}</h3><p>${escape(m.notes)}</p><pre>${escape(JSON.stringify({normalization:m.normalization,escalation_weights:m.escalation_weights,scenario_weights:m.scenario_weights},null,2))}</pre><h3>Temporal integrity</h3><p>Rainfall totals use complete hours before the selected acquisition. Radar decrease persistence uses only observations available at or before that date. Rainfall predictor windows are disjoint; recency-weighted pressure is disclosed separately. Scenario duration scales the last D observed hourly rates, not a forecast. Terrain mesh exaggeration is presentation only.</p><h3>Missing evidence stays missing</h3><p>Historical flood response has no labeled repeat cases. Model confidence and validation metrics remain null, not fabricated. Thermal imagery is not used to increase the flood score. Index bands describe an illustrative model, not certain events.</p><ul>${state.manifest.limitations.map(text=>`<li>${escape(text)}</li>`).join('')}</ul><h3>Thermal quality</h3><p>${escape(state.thermal.qa_rule)} Native TIRS detail is 100 m; the delivered 30 m grid does not create additional thermal detail. Dates, cloud-screened coverage and reported uncertainty are visible in the inspector.</p><ul>${state.thermal.limitations.map(text=>`<li>${escape(text)}</li>`).join('')}</ul><h3>Download provenance</h3><p><a href="${floodBase}model.json" download>Model card ↓</a> · <a href="${floodBase}manifest.json" download>Flood evidence manifest ↓</a> · <a href="${thermalBase}manifest.json" download>Thermal sources and quality ↓</a></p><pre>Input bundle SHA-256: ${escape(state.manifest.inputs_sha256)}\nProducing code SHA-256: ${escape(state.manifest.source_code_sha256)}</pre>`;
}
$('open-geography').addEventListener('click',()=>$('geography-dialog').showModal());$('close-geography').addEventListener('click',()=>$('geography-dialog').close());
$('evidence-tab').addEventListener('click',()=>setInspector(false));$('scenario-tab').addEventListener('click',()=>{player?.pause();setInspector(true);});
$('rain-multiplier').addEventListener('input',event=>{state.parameters.rainfall_multiplier=Number(event.target.value);$('rain-value').innerHTML=fmt(state.parameters.rainfall_multiplier,2)+'<span>×</span>';$('scenario-message').textContent='Controls changed. Run to apply this counterfactual.';});
for(const button of document.querySelectorAll('[data-duration]'))button.addEventListener('click',()=>{state.parameters.duration_hours=Number(button.dataset.duration);document.querySelectorAll('[data-duration]').forEach(b=>b.classList.toggle('active',b===button));$('scenario-message').textContent='Duration changed. Run to scale this observed-hour window.';});
for(const button of document.querySelectorAll('[data-wetness]'))button.addEventListener('click',()=>{state.parameters.wetness=button.dataset.wetness;document.querySelectorAll('[data-wetness]').forEach(b=>b.classList.toggle('active',b===button));$('scenario-message').textContent='Wetness assumption changed. Run to apply it.';});
for(const button of document.querySelectorAll('[data-preset]'))button.addEventListener('click',()=>{state.parameters.rainfall_multiplier=Number(button.dataset.preset);$('rain-multiplier').value=state.parameters.rainfall_multiplier;$('rain-value').innerHTML=fmt(state.parameters.rainfall_multiplier,2)+'<span>×</span>';runScenario();});
$('run-scenario').addEventListener('click',runScenario);
$('clear-scenario').addEventListener('click',()=>{state.scenario=null;state.probe=null;state.layer='escalation';$('clear-scenario').hidden=true;document.querySelector('[data-layer="delta"]').disabled=true;renderMap().catch(error);});
for(const button of document.querySelectorAll('[data-layer]'))button.addEventListener('click',()=>{player?.pause();state.layer=button.dataset.layer;state.probe=null;renderMap().catch(error);});
$('compare-slider').addEventListener('input',event=>{if(terrain){terrain.split=Number(event.target.value)/100;terrain.draw();}});
$('focus-thermal').addEventListener('click',()=>{if(!state.scene?.clear_focus_tile)return;player?.pause();state.layer='thermal';terrain.focus(state.scene.clear_focus_tile);renderMap().catch(error);});
$('thermal-scene').addEventListener('change',event=>{player?.pause();state.scene=state.thermal.scenes.find(scene=>scene.scene_id===event.target.value);if(['thermal','optical'].includes(state.layer))renderMap().catch(error);else renderThermal();});
$('view-2d').addEventListener('click',()=>{terrain?.setMode('2d');$('view-2d').classList.add('active');$('view-3d').classList.remove('active');$('orbit').setAttribute('aria-pressed','false');$('terrain-note').textContent='North-up · 24 × 24 km study area';$('map-instruction').textContent='Click to inspect a model cell';});
$('view-3d').addEventListener('click',()=>{if(!terrain?.setMode('3d'))return;$('view-3d').classList.add('active');$('view-2d').classList.remove('active');$('terrain-note').textContent='NASADEM · height ×4 for display';$('map-instruction').textContent='Drag to orbit · click to inspect';});
$('orbit').addEventListener('click',()=>{if(!terrain)return;const value=!terrain.auto;terrain.setAuto(value);$('orbit').setAttribute('aria-pressed',String(terrain.auto));});
$('zoom-in').addEventListener('click',()=>{if(terrain){terrain.zoom=Math.min(4,terrain.zoom*1.3);terrain.draw();}});$('zoom-out').addEventListener('click',()=>{if(terrain){terrain.zoom=Math.max(.7,terrain.zoom/1.3);terrain.draw();}});$('reset-map').addEventListener('click',()=>terrain?.reset());
$('expand-map').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await $('map-card').requestFullscreen();}catch(cause){error(cause);}});
$('reset-probe').addEventListener('click',()=>{state.probe=null;if(terrain){terrain.marker=null;terrain.draw();}renderEvidence();});
$('open-sources').addEventListener('click',()=>$('sources-dialog').showModal());$('close-sources').addEventListener('click',()=>$('sources-dialog').close());
$('play').addEventListener('click',()=>{if(player?.snapshot().playing)player.pause();else player?.play();});$('restart').addEventListener('click',()=>player?.seek(0));$('speed').addEventListener('change',event=>player?.setDelay(Number(event.target.value)));$('loop').addEventListener('change',event=>player?.setLoop(event.target.checked));
document.addEventListener('visibilitychange',()=>{if(document.hidden){player?.pause();terrain?.setAuto(false);$('orbit').setAttribute('aria-pressed','false');}});window.addEventListener('pagehide',()=>{player?.destroy();terrain?.setAuto(false);});
$('export-evidence').addEventListener('click',()=>{const record={observation:observation(),model_version:state.manifest.model.model_version,inputs_sha256:state.manifest.inputs_sha256,scenario:state.scenario,selected_cell:state.probe,thermal_scene:state.scene,limitations:state.manifest.limitations};const url=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='terrapulse-evidence-'+observation().timestamp.slice(0,10)+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
try{
  const [manifest,timeline,thermal,mesh,geography,dna]=await Promise.all([localJSON('/api/cases/nepal_case_01/flood-escalation'),localJSON('/api/cases/nepal_case_01/timeline'),localJSON('/api/cases/nepal_case_01/thermal'),localJSON(floodBase+'terrain_mesh.json'),localJSON(floodBase+'geographic_check.json'),localJSON(base+'dna/manifest.json')]);
  state.manifest=manifest;state.dna=dna;state.timeline=timeline;state.thermal=thermal;state.index=manifest.observations.length-1;
  terrain=new TerrainView($('landscape'),mesh,{onPick:inspectCell,onStatus:text=>{$('terrain-note').textContent=text;$('view-3d').disabled=true;$('view-3d').classList.remove('active');$('view-2d').classList.add('active');$('orbit').disabled=true;$('map-instruction').textContent='2D fallback · click to inspect';}});
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches)$('orbit').disabled=true;
  $('dates').innerHTML=manifest.observations.map((obs,index)=>`<button data-date="${index}"><span>${escape(day(obs.timestamp))}</span><small>${index===0?'BASELINE':index===manifest.observations.length-1?'LATEST RADAR':'REPEAT OBSERVATION'}</small></button>`).join('');
  $('thermal-scene').innerHTML=thermal.scenes.filter(scene=>scene.valid_fraction>0).map(scene=>`<option value="${escape(scene.scene_id)}">${escape(day(scene.datetime))} · ${fmt(scene.valid_fraction*100,1)}% thermal</option>`).join('');$('thermal-scene').disabled=!thermal.scenes.some(scene=>scene.valid_fraction>0);
  player=createPlayback({count:manifest.observations.length,initialIndex:state.index,show:selectObservation,onState:p=>{$('play').textContent=p.playing?'Ⅱ Pause':'▶ Play dates';$('play').setAttribute('aria-pressed',String(p.playing));},onError:error});
  document.querySelectorAll('[data-date]').forEach(button=>button.addEventListener('click',()=>player.seek(Number(button.dataset.date))));
  $('play').disabled=false;$('restart').disabled=false;$('run-scenario').disabled=false;$('export-evidence').disabled=false;
  renderGeography(geography);buildSources();await selectObservation(state.index);
}catch(cause){error(cause);}
