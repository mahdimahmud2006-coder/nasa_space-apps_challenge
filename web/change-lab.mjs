import {TerrainView} from '/terrain-view.mjs';
import {createPlayback} from '/playback.mjs';
const $=id=>document.getElementById(id),base='/cases/nepal_case_01/',landslideBase=base+'landslide/';
const fmt=(value,digits=1)=>value===null||value===undefined?'Unavailable':Number(value).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date=value=>new Date(value).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
const state={dna:null,landslide:null,flood:null,timeline:null,index:0,layer:'radar',zone:null,probe:null,generation:0,story:0};
let terrain=null,player=null;
async function json(path){const response=await fetch(path);if(!response.ok)throw new Error('Local Change Lab evidence is unavailable. Generate it with make change-lab and restart make run.');return response.json();}
function fail(cause){$('lab-error').hidden=false;$('lab-error').textContent=cause.message;$('lab-loading').hidden=true;player?.pause();}
const observation=()=>state.landslide.observations[state.index];
const profile=()=>state.dna.profiles.find(p=>p.zone_id===state.zone);
function renderDNA(){
 const p=profile();if(!p){$('dna-labels').textContent='No tracked zones in this case.';return;}
 const f=p.features;
 $('dna-labels').innerHTML=p.labels.map(label=>`<span>${esc(label)}</span>`).join('');
 const metrics=[['Peak radar magnitude',fmt(f.magnitude_db,2)+' dB','Mean absolute change from baseline'],['Onset bracket',p.onset_bracket?date(p.onset_bracket[0])+' → '+date(p.onset_bracket[1]):'Unavailable','Exact onset is unresolved'],['Average onset rate',fmt(f.onset_rate_db_per_day,3)+' dB/day','Across baseline → first disturbed visit'],['Peak area growth',fmt(f.peak_growth_km2_per_day,5)+' km²/day','Successive change-mask area; negative means contraction'],['Disturbance persistence',fmt(f.persistence===null?null:f.persistence*100,0)+'%',p.persistence_denominator+' valid post-onset visits'],['Return toward baseline',fmt(f.recovery===null?null:f.recovery*100,1)+'%','Descriptive recovery, not physical restoration'],['Peak candidate area',fmt(f.peak_candidate_area_km2,4)+' km²','Retained radar change-mask area'],['Temporal variability',fmt(f.variability_db,3)+' dB','Post-baseline magnitude standard deviation'],['Rain before first disturbed visit',fmt(f.rain_24h_mm,1)+' / '+fmt(f.rain_72h_mm,1)+' mm','24 / 72 complete hours; regional model'],['Mean zone slope',fmt(f.slope_deg,2)+'°','Historical NASADEM context'],['Data coverage',p.data_coverage_fraction===null?'Unavailable':fmt(p.data_coverage_fraction*100,1)+'%',p.valid_observation_count+' / '+p.observation_count+' radar visits'],['Thermal anomaly / confidence','Unavailable','No matched thermal anomaly baseline or model calibration']];
 $('dna-features').innerHTML=metrics.map(([label,value,note])=>`<dt>${esc(label)}<small>${esc(note)}</small></dt><dd>${esc(value)}</dd>`).join('');
 $('dna-censoring').innerHTML=p.recovery_half_life_censored?`<strong>Recovery half-life is right-censored.</strong><br>No observed visit fell below half the peak during ${fmt(p.recovery_followup_days,0)} days of follow-up. Missing visits are not interpolated.`:p.recovery_half_life_bracket_days?`Half-peak crossing lies between ${fmt(p.recovery_half_life_bracket_days[0],1)} and ${fmt(p.recovery_half_life_bracket_days[1],1)} days after the observed peak.`:'Recovery half-life is unavailable.';
 $('dna-similar').innerHTML=p.similarity.available?`<strong>Similar radar behavior</strong><ul>${p.similarity.matches.map(m=>`<li>${esc(m.zone_id)} · ${fmt(m.similarity,3)} cosine similarity</li>`).join('')}</ul><p>Similarity does not identify a disaster.</p>`:`<strong>Similar-event search: insufficient references.</strong><br>${esc(p.similarity.reason)} No historical matches or percentiles are invented.`;
 const points=p.observations,width=430,height=205,left=48,right=20,top=28,bottom=38;
 const start=new Date(points[0].timestamp).getTime(),span=Math.max(1,new Date(points.at(-1).timestamp)-start),max=Math.max(1,...points.map(r=>r.mean_absolute_delta_from_baseline_db||0))*1.15;
 const x=r=>left+(new Date(r.timestamp)-start)/span*(width-left-right),y=r=>height-bottom-r.mean_absolute_delta_from_baseline_db/max*(height-bottom-top);
 let segments=[];
 for(let i=1;i<points.length;i++)if(points[i-1].mean_absolute_delta_from_baseline_db!==null&&points[i].mean_absolute_delta_from_baseline_db!==null)segments.push(`M${x(points[i-1])},${y(points[i-1])}L${x(points[i])},${y(points[i])}`);
 $('dna-curve').innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Sampled mean absolute baseline radar change in dB over elapsed days"><text x="4" y="20">dB</text><text x="4" y="42">${fmt(max,1)}</text><text x="18" y="${height-bottom}">0</text><line class="axis" x1="${left}" x2="${width-right}" y1="${height-bottom}" y2="${height-bottom}"/><path class="curve" d="${segments.join('')}"/>${points.filter(r=>r.mean_absolute_delta_from_baseline_db!==null).map(r=>`<circle cx="${x(r)}" cy="${y(r)}" r="5" class="${r.observation_id===observation().observation_id?'current':''}"><title>${esc(date(r.timestamp))}: ${fmt(r.mean_absolute_delta_from_baseline_db,2)} dB</title></circle><text x="${x(r)}" y="${height-10}" text-anchor="middle">${fmt((new Date(r.timestamp)-start)/86400000,0)} d</text>`).join('')}</svg>`;
}
function renderScore(){
 const obs=observation(),record=state.probe||obs,score=state.probe?record.score:obs.summary.mean_score;
 $('lab-score').textContent=fmt(score,1);
 $('lab-class').textContent=score===null?'Not assessable':state.landslide.model.score_classes[state.landslide.model.score_boundaries.filter(t=>score>=t).length]+' index';
 $('lab-score-scope').textContent=state.probe?'Selected saved 30 m model cell.':'Mean across assessable cells; click the map for a cell explanation.';
 const entries=Object.entries(record.contributions).filter(([,v])=>v!==null),maximum=Math.max(1,...entries.map(([,v])=>v));
 $('lab-contributions').innerHTML=entries.map(([key,value])=>`<div class="contribution-row"><div class="contribution-label"><span>${esc(state.landslide.model.feature_labels[key])}</span><strong>+${fmt(value,2)}</strong></div><div class="contribution-bar"><i style="width:${value/maximum*100}%"></i></div></div>`).join('');
 $('lab-probe-detail').textContent=state.probe?`${fmt(state.probe.latitude,5)}° N, ${fmt(state.probe.longitude,5)}° E · contributions sum to the selected index.`:'Contributions sum to the AOI index. They explain model arithmetic, not causation.';
 $('lab-clear-probe').hidden=!state.probe;$('lab-quality').textContent=fmt(obs.summary.coverage_fraction*100,1)+'%';
 const comparison=obs.shared_footprint_comparison;
 $('compare-flood').textContent=fmt(comparison.flood_mean,1)+' / 100';$('compare-landslide').textContent=fmt(comparison.landslide_mean,1)+' / 100';
 const tiles=obs.attention_tiles.slice(0,5);
 $('lab-tiles').innerHTML=tiles.map((tile,i)=>`<button data-lab-tile="${i}"><span class="rank">${i+1}</span><span class="tile-id">${esc(tile.tile_id)}<small>${fmt(tile.high_area_km2,3)} km² with index ≥ 50</small></span><strong>${fmt(tile.mean_score,1)}</strong></button>`).join('');
 document.querySelectorAll('[data-lab-tile]').forEach(b=>b.addEventListener('click',()=>{player.pause();terrain.focus(tiles[Number(b.dataset.labTile)]);}));
}
async function renderMap(){
 const token=++state.generation,obs=observation();$('lab-loading').hidden=false;$('lab-landscape').setAttribute('aria-busy','true');
 const layers={total:[obs.total_preview,'Combined landslide susceptibility','Static terrain + preceding rainfall + radar disturbance × slope. Uncalibrated attention, not a forecast.'],static:[state.landslide.static_preview,'Static terrain susceptibility','Slope, roughness, absolute curvature, TWI and modeled drainage. Historical terrain; illustrative frozen weights.'],dynamic:[obs.dynamic_preview,'Prior rainfall trigger','Disjoint 0–24, 24–72 and 72–168 h regional NASA POWER rainfall windows. This map adds no local rainfall resolution.'],modifier:[obs.modifier_preview,'Radar disturbance × slope','Mean absolute baseline dB change × slope support; ambiguity and missingness preserved. This is not landslide identification.']};
 let layer,caption,title,radar=false;
 if(state.layer==='flood'){layer=base+'flood/'+state.flood.observations[state.index].escalation_preview;title='Flood attention · different formula';caption='Low-slope valley model for comparison. Flood and landslide indices are different, uncalibrated models.';}
 else if(state.layer==='radar'){layer=base+'timeseries/'+state.timeline.observations[state.index].preview;title='NISAR HH backscatter';caption='Gamma-0 dB preview with shared contrast; PROVISIONAL. This is a measured radar observation, not a hazard mask.';radar=true;}
 else{const item=layers[state.layer];layer=landslideBase+item[0];title=item[1];caption=item[2];}
 terrain.opacity=.88;terrain.split=1;await terrain.setImages(base+'flood/relief.png',layer,layer);if(token!==state.generation)return;
 $('lab-map-date').textContent=date(obs.timestamp)+' · NISAR';$('lab-caption').textContent=caption;$('lab-coverage').textContent=fmt(obs.summary.coverage_fraction*100,1)+'% total assessed';
 $('lab-legend-low').textContent=radar?'Low':'0';$('lab-legend-mid').textContent=radar?'Shared contrast':'50';$('lab-legend-high').textContent=radar?'High':'100';
 $('lab-legend-title').textContent=title;$('lab-legend-note').textContent=radar?'Low → high shared dB contrast; no probability scale.':'Index points, not probability. Missing cells stay hatched.';
 document.querySelectorAll('[data-lab-layer]').forEach(b=>{b.classList.toggle('active',b.dataset.labLayer===state.layer);b.disabled=b.dataset.labLayer==='modifier'&&!obs.radar_available;});
 document.querySelectorAll('[data-lab-date]').forEach(b=>{const current=Number(b.dataset.labDate)===state.index;b.classList.toggle('active',current);if(current)b.setAttribute('aria-current','date');else b.removeAttribute('aria-current');});
 $('lab-loading').hidden=true;$('lab-landscape').setAttribute('aria-busy','false');renderScore();renderDNA();
}
async function select(index){state.index=index;state.probe=null;if(state.layer==='modifier'&&!observation().radar_available)state.layer='total';await renderMap();}
async function inspect(point){
 player.pause();if(state.layer==='flood'||state.layer==='radar'){$('lab-probe-detail').textContent='Select a landslide component layer to inspect its susceptibility cell.';return;}
 const token=state.generation;
 try{const probe=await json('/api/cases/nepal_case_01/landslide-probe?'+new URLSearchParams({observation_id:observation().observation_id,row:point.row,col:point.col}));if(token!==state.generation)return;state.probe=probe;renderScore();}catch(cause){fail(cause);}
}
function focusZone(){
 const p=profile();if(!p?.geometry.bbox_projected)return;
 const [left,bottom,right,top]=p.geometry.bbox_projected,g=state.landslide.grid.affine;
 const col=(left+right)/2,row=(bottom+top)/2;
 terrain.focus({row_start:Math.max(0,Math.floor((g[5]-row)/Math.abs(g[4]))-20),col_start:Math.max(0,Math.floor((col-g[2])/g[0])-20),height:40,width:40});
}
const story=[
 ['Start with what was observed.','Saved radar visits show surface changes. They do not identify a disaster.','radar'],
 ['Read the behavior, not just the image.','This tracked zone retains a baseline radar disturbance while its successive change mask contracts. Change DNA makes that distinction visible.','radar'],
 ['Ask why hillsides deserve inspection.','Terrain and preceding rain are separate contributors. Radar disturbance on a slope adds supporting evidence, not a confirmed landslide.','total'],
 ['Show the evidence gap.','Independent validation is part of the story. Missing labels, coarse rainfall, uncertain causes and a small temporal sample remain visible.','static']
];
async function showStory(index){
 player.pause();state.story=index;state.probe=null;const [title,copy,layer]=story[index];state.layer=layer;
 $('story-count').textContent=`FOLLOW THE EVIDENCE · ${index+1} / ${story.length}`;$('story-title').textContent=title;$('story-copy').textContent=copy;
 $('story-back').disabled=index===0;$('story-next').textContent=index===story.length-1?'Restart story ↺':'Next question →';
 if(index===1)focusZone();else terrain.reset();await renderMap();
}
function methods(){
 $('lab-methods-content').innerHTML=`<h3>Change DNA · ${esc(state.dna.model_version)}</h3><dl>${Object.entries(state.dna.formulas).map(([k,v])=>`<dt><strong>${esc(k)}</strong></dt><dd><p>${esc(v)}</p></dd>`).join('')}</dl><h3>Landslide susceptibility · ${esc(state.landslide.model.model_version)}</h3><p>${esc(state.landslide.model.notes)}</p><pre>${esc(JSON.stringify({formulas:state.landslide.model.formulas,static_weights:state.landslide.model.static_weights,rain_weights:state.landslide.model.rain_weights,combined_weights:state.landslide.model.combined_weights,normalization:state.landslide.model.normalization_bounds},null,2))}</pre><h3>Independent evidence and source policy</h3><p>NASA/GSFC catalog, NASA POWER and NASADEM sources are served or distributed by NASA and Microsoft. No Chinese government or agency data source is used for these additions. Provider provenance is recorded; this does not certify competition eligibility.</p><p><a href="https://data.nasa.gov/dataset/global-landslide-catalog-export-f07b6" target="_blank" rel="noreferrer">NASA catalog ↗</a> · <a href="https://github.com/nasa/LHASA" target="_blank" rel="noreferrer">NASA LHASA research context ↗</a></p><p>TerraPulse is a separate illustrative model; NASA LHASA is not reproduced or claimed as its validation.</p><ul>${[...state.dna.limitations,...state.landslide.limitations].map(v=>`<li>${esc(v)}</li>`).join('')}</ul><h3>Reproduce and inspect</h3><p><a href="${base}dna/manifest.json" download>DNA manifest ↓</a> · <a href="${landslideBase}manifest.json" download>Landslide model and evidence ↓</a> · <a href="${landslideBase}landslide_validation.json" download>Validation status ↓</a></p>`;
 const validation=state.landslide.validation;
 $('lab-validation').innerHTML=`<p><strong>${esc(validation.status.replaceAll('_',' '))}</strong></p><p>${validation.catalog_points_in_aoi} NASA catalog reports in this AOI; ${validation.usable_point_count} eligible historical reports in ${validation.occupied_blocks} spatial blocks.</p><p>${esc(validation.reason)}</p><p>${esc(validation.interpretation)}</p><p><a href="https://data.nasa.gov/dataset/global-landslide-catalog-export-f07b6" target="_blank" rel="noreferrer">NASA independent reference catalog ↗</a></p>`;
}
$('story-next').addEventListener('click',()=>showStory((state.story+1)%story.length).catch(fail));$('story-back').addEventListener('click',()=>showStory(Math.max(0,state.story-1)).catch(fail));
$('dna-zone').addEventListener('change',event=>{state.zone=event.target.value;renderDNA();});$('focus-dna').addEventListener('click',()=>{player.pause();focusZone();});
for(const b of document.querySelectorAll('[data-lab-layer]'))b.addEventListener('click',()=>{player.pause();state.layer=b.dataset.labLayer;state.probe=null;renderMap().catch(fail);});
$('lab-2d').addEventListener('click',()=>{terrain.setMode('2d');$('lab-2d').classList.add('active');$('lab-3d').classList.remove('active');});$('lab-3d').addEventListener('click',()=>{if(terrain.setMode('3d')){$('lab-3d').classList.add('active');$('lab-2d').classList.remove('active');}});$('lab-reset').addEventListener('click',()=>terrain.reset());
$('lab-clear-probe').addEventListener('click',()=>{state.probe=null;terrain.marker=null;terrain.draw();renderScore();});
$('lab-play').addEventListener('click',()=>player.snapshot().playing?player.pause():player.play());$('lab-loop').addEventListener('change',event=>player.setLoop(event.target.checked));
$('show-methods').addEventListener('click',()=>$('lab-methods').showModal());$('lab-close-methods').addEventListener('click',()=>$('lab-methods').close());
$('lab-export').addEventListener('click',()=>{const payload={case_id:state.landslide.case_id,observation_id:observation().observation_id,dna:profile(),landslide_observation:observation(),selected_cell:state.probe,model:state.landslide.model,validation:state.landslide.validation,input_hashes:{dna:state.dna.input_hashes,landslide:state.landslide.input_hashes},limitations:[...state.dna.limitations,...state.landslide.limitations]};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='terrapulse-change-dna-'+observation().timestamp.slice(0,10)+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)player?.pause();});window.addEventListener('pagehide',()=>player?.destroy());
try{
 const [dna,landslide,flood,timeline,mesh]=await Promise.all([json(base+'dna/manifest.json'),json(base+'landslide/manifest.json'),json(base+'flood/manifest.json'),json(base+'timeseries/timeline.json'),json(base+'flood/terrain_mesh.json')]);
 state.dna=dna;state.landslide=landslide;state.flood=flood;state.timeline=timeline;state.zone=dna.profiles[0]?.zone_id||null;state.index=landslide.observations.length-1;
 terrain=new TerrainView($('lab-landscape'),mesh,{onPick:inspect,onStatus:text=>{$('lab-terrain-note').textContent=text;$('lab-3d').disabled=true;$('lab-3d').classList.remove('active');$('lab-2d').classList.add('active');}});
 $('dna-zone').innerHTML=dna.profiles.map(p=>`<option value="${esc(p.zone_id)}">${esc(p.zone_id)}</option>`).join('');$('dna-zone').disabled=dna.profiles.length<2;
 $('focus-dna').disabled=!state.zone;
 $('lab-dates').innerHTML=landslide.observations.map((obs,i)=>`<button data-lab-date="${i}"><span>${esc(date(obs.timestamp))}</span><small>${i===0?'BASELINE · NO RADAR COMPARISON':'SAVED REPEAT OBSERVATION'}</small></button>`).join('');
 player=createPlayback({count:landslide.observations.length,initialIndex:state.index,show:select,delay:2000,onState:p=>{$('lab-play').textContent=p.playing?'Ⅱ Pause':'▶ Play dates';$('lab-play').setAttribute('aria-pressed',String(p.playing));},onError:fail});
 document.querySelectorAll('[data-lab-date]').forEach(b=>b.addEventListener('click',()=>player.seek(Number(b.dataset.labDate))));
 for(const id of ['story-next','show-methods','lab-2d','lab-reset','lab-loop'])$(id).disabled=false;
 $('lab-3d').disabled=!terrain.gl;$('lab-play').disabled=false;$('lab-export').disabled=false;methods();await select(state.index);
}catch(cause){fail(cause);}
