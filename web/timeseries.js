import {createPlayback} from '/playback.mjs';
const byId=id=>document.getElementById(id);
const base='/cases/nepal_case_01/timeseries/';
const number=(value,digits=4)=>value===null||value===undefined?'Not assessable':Number(value).toLocaleString('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits});
const percentage=value=>value===null||value===undefined?'Not assessable':number(value*100,1)+'%';
const escaped=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const day=value=>new Date(value).toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
const model={timeline:null,rows:[],display:[],index:0,zone:null,layer:'observation',context:null,contextLayer:'',generation:0,displayIndex:0};
let player=null;
const decodedImages=new Map();
function loadImage(url){
  if(!decodedImages.has(url)){const image=new Image();image.src=url;decodedImages.set(url,image.decode().then(()=>image).catch(error=>{decodedImages.delete(url);throw error;}));}
  return decodedImages.get(url);
}
async function localJson(path){const response=await fetch(path);if(!response.ok)throw new Error(`Saved time-series evidence unavailable (${response.status}). Run make timeseries from the project folder.`);return response.json();}
function row(label,value){return `<div class="evidence-row"><span>${escaped(label)}</span><strong>${escaped(value)}</strong></div>`;}
function errorMessage(error){player?.pause();byId('temporal-map').setAttribute('aria-busy','false');byId('temporal-error').hidden=false;byId('temporal-error').textContent=error.message;}
function lineChart(id,points,unit,{domain=null,onSelect=null}={}){
  const finite=points.filter(p=>p.value!==null&&p.value!==undefined&&Number.isFinite(p.value));
  if(!finite.length){byId(id).textContent='No assessable measurements.';return;}
  const width=520,height=190,left=62,right=22,top=16,bottom=42;
  const dates=points.map(p=>new Date(p.timestamp).getTime()),minTime=Math.min(...dates),span=Math.max(1,Math.max(...dates)-minTime);
  let low=domain?domain[0]:Math.min(0,...finite.map(p=>p.value)),high=domain?domain[1]:Math.max(0,...finite.map(p=>p.value));
  if(high===low)high=low+1;
  const x=p=>left+(new Date(p.timestamp).getTime()-minTime)/span*(width-left-right);
  const y=p=>top+(high-p.value)/(high-low)*(height-top-bottom);
  let paths=[],run=[];
  for(const point of points){if(point.value===null||point.value===undefined||!Number.isFinite(point.value)){if(run.length)paths.push(run);run=[];}else run.push(point);}
  if(run.length)paths.push(run);
  byId(id).innerHTML=`<svg viewBox="0 0 ${width} ${height}" aria-label="${escaped(unit)}"><path class="axis" d="M${left},${top}V${height-bottom}H${width-right}"/><text x="4" y="${top+8}">${number(high,high<.1?4:2)}</text><text x="4" y="${height-bottom}">${number(low,2)}</text>${paths.map(segment=>`<path class="line" d="${segment.map((p,i)=>(i?'L':'M')+x(p)+','+y(p)).join(' ')}"/>`).join('')}${finite.map((p,i)=>`<circle cx="${x(p)}" cy="${y(p)}" r="4" data-point="${i}" data-timestamp="${escaped(p.timestamp)}"><title>${escaped(day(p.timestamp))}: ${number(p.value)} ${escaped(unit)}</title></circle>`).join('')}${points.map(p=>`<text x="${x(p)}" y="${height-15}" text-anchor="middle">${escaped(day(p.timestamp).slice(0,6))}</text>`).join('')}</svg>`;
  if(onSelect)byId(id).querySelectorAll('circle').forEach((element,i)=>{element.style.cursor='pointer';element.setAttribute('tabindex','0');element.setAttribute('role','button');element.setAttribute('aria-label',`Select ${day(finite[i].timestamp)}`);element.addEventListener('click',()=>onSelect(finite[i]));element.addEventListener('keydown',e=>{if(e.key==='Enter')onSelect(finite[i]);});});
}
function drawZones(){
  const svg=byId('zone-hits'),[height,width]=model.timeline.canonical_grid.shape;
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);svg.replaceChildren();
  for(const item of model.display){
    const geometry=item.geometry_pixel,polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
    const path=document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d',polygons.map(polygon=>polygon.map(ring=>'M'+ring.map(p=>p.join(',')).join('L')+'Z').join('')).join(''));
    path.setAttribute('fill-rule','evenodd');path.classList.toggle('selected',item.zone_id===model.zone?.zone_id);
    path.setAttribute('role','button');path.setAttribute('tabindex','0');path.setAttribute('aria-label',`Inspect ${item.zone_id}`);
    path.addEventListener('click',()=>selectZone(item.zone_id));path.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectZone(item.zone_id);}});svg.append(path);
  }
}
function renderContext(){
  const item=model.context?.zone_context.find(r=>r.zone_id===model.zone?.zone_id&&r.observation_id===model.timeline.observations[model.displayIndex].observation_id);
  if(!item){byId('environmental-context').textContent='Saved environmental context unavailable for this zone and date.';return;}
  byId('environmental-context').innerHTML=`${row('Precipitation · previous 24 h',number(item.rainfall_mm_24h,1)+' mm')}${row('Precipitation · previous 72 h',number(item.rainfall_mm_72h,1)+' mm')}${row('Precipitation · previous 7 days',number(item.rainfall_mm_168h,1)+' mm')}${row('Elevation · EGM96',number(item.elevation_m,0)+' m')}${row('Mean / maximum slope',number(item.slope_deg,1)+'° / '+number(item.max_slope_deg,1)+'°')}${row('Modeled wetness · TWI',number(item.twi,2))}${row('Mean modeled drainage distance',number(item.distance_to_drainage_m,0)+' m')}<p class="caption">NASA POWER · regional model/reanalysis at 0.5° × 0.625° (roughly 50–60 km). Totals end ${escaped(item.rainfall_window_end_utc)}, ${number(item.rainfall_end_lag_seconds/60,1)} minutes before acquisition. NASADEM native 1 arc-second. ${item.distinct_terrain_cells} terrain cells intersect this zone. Wetness and drainage are uncalibrated terrain models.</p>`;
}
function selectZone(zoneId){
  model.zone=model.timeline.zones.find(zone=>zone.zone_id===zoneId)||null;
  byId('focus-zone').disabled=!model.zone;renderContext();
  if(!model.zone){byId('zone-evidence').textContent='No zones passed the retained candidate rule. No zone is invented.';byId('zone-chart').textContent='No tracked zone.';byId('recovery-chart').textContent='Not assessable.';return;}
  const zone=model.zone,rows=model.rows.filter(r=>r.zone_id===zoneId),current=rows[model.displayIndex];byId('zone-select').value=zoneId;
  const bracket=zone.onset_bracket?zone.onset_bracket.map(day).join(' → '):'Not established';
  byId('zone-evidence').innerHTML=`<h2>${escaped(zoneId)}</h2>${row('Fixed footprint',number(zone.footprint_area_km2)+' km²')}${row('First detection bracket',bracket)}${row('Peak interval candidate area',number(zone.peak_area_km2)+' km²')}${row('Detected / observed intervals',zone.detected_intervals+' / '+zone.observed_intervals)}${row('Transition frequency',percentage(zone.persistence))}${row('Mean signed Δ from baseline',number(current?.mean_delta_from_baseline_db,2)+' dB')}${row('Recovery at selected date',percentage(current?.recovery))}${row('Latest descriptive status',zone.status.replaceAll('_',' '))}<p class="caption">Cause: ${escaped(zone.validation_status)}. The onset bracket is constrained by observation dates. Repeated candidate transitions do not establish a sustained physical disturbance.</p>`;
  lineChart('zone-chart',rows.map(r=>({timestamp:r.timestamp,value:r.mean_delta_from_baseline_db})),'dB');
  lineChart('recovery-chart',rows.map(r=>({timestamp:r.timestamp,value:r.recovery})),'fraction',{domain:[0,1]});drawZones();
}
function highlightDate(){
  const timestamp=model.timeline.observations[model.displayIndex].timestamp;
  document.querySelectorAll('.chart circle[data-timestamp]').forEach(dot=>dot.classList.toggle('current',dot.dataset.timestamp===timestamp));
}
function fadePreviousFrame(){
  const stage=byId('temporal-stage');stage.querySelectorAll('.frame-ghost').forEach(node=>node.remove());
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches||!byId('observation-image').getAttribute('src'))return null;
  const ghost=document.createElement('div');ghost.className='frame-ghost';ghost.setAttribute('aria-hidden','true');
  for(const id of ['observation-image','temporal-overlay']){const source=byId(id);if(!source.hidden){const copy=source.cloneNode();copy.removeAttribute('id');copy.removeAttribute('alt');ghost.append(copy);}}
  stage.append(ghost);return ghost;
}
async function renderObservation(){
  if(!model.timeline)return;
  const generation=++model.generation,index=model.index,timeline=model.timeline,obs=timeline.observations[index],interval=index?timeline.intervals[index-1]:null;
  byId('temporal-map').setAttribute('aria-busy','true');
  let layerPath=null,description='HH gamma-0 backscatter · identical contrast across all observations.';
  if(model.layer==='candidates'){layerPath=interval?interval.overlay:null;description=interval?`${day(interval.start)} → ${day(interval.end)} · successive exploratory candidates after identical cleanup.`:'The first observation is the baseline; there is no preceding interval.';}
  if(model.layer==='persistence'){layerPath='persistence.png';description='Series-wide retained candidate transition frequency. This overlay stays fixed while the observation changes. Dark = 0, light = 1; pixels missing any interval excluded.';}
  if(model.layer==='recovery'){layerPath='recovery.png';description='Latest series-wide return toward baseline. This overlay stays fixed while the observation changes. Dark = near peak, light = toward baseline; unassessable pixels excluded.';}
  let contextPath=null;
  if(model.layer==='context'&&model.context){
    const item=model.context.observations.find(o=>o.observation_id===obs.observation_id);
    const selected=item?.layers[model.contextLayer]||model.context.terrain_layers[model.contextLayer];
    if(selected){contextPath='/cases/nepal_case_01/context/'+selected.preview;description=`${selected.definition}. Color range ${number(selected.display_range[0],1)}–${number(selected.display_range[1],1)} ${selected.units}. `+(model.contextLayer.startsWith('rain_')?'Native precipitation resolution 0.5° × 0.625°; 30 m display adds no detail.':'Static terrain context at 30 m; this layer stays fixed across dates. Hydrology is model-derived.');}
  }
  const overlayUrl=contextPath||(layerPath?base+layerPath:null);
  const [image,layer]=await Promise.all([loadImage(base+obs.preview),overlayUrl?loadImage(overlayUrl):null]);
  if(generation!==model.generation)return;
  // Commit map, date and evidence together after both images have decoded.
  const ghost=index!==model.displayIndex?fadePreviousFrame():null;
  model.displayIndex=index;
  byId('observation-image').src=image.src;
  const overlay=byId('temporal-overlay');overlay.hidden=!layer;overlay.style.opacity=contextPath?'1':'.8';if(layer)overlay.src=layer.src;
  if(ghost){if(typeof ghost.animate==='function'){const animation=ghost.animate([{opacity:1},{opacity:0}],{duration:240,easing:'ease-out'});animation.finished.then(()=>ghost.remove()).catch(()=>ghost.remove());}else ghost.remove();}
  byId('date-slider').value=index;byId('selected-date').textContent=day(obs.timestamp);byId('selected-date').dateTime=obs.timestamp;
  byId('map-date').textContent=day(obs.timestamp)+' · UTC';byId('map-date').dateTime=obs.timestamp;
  byId('date-slider').setAttribute('aria-valuetext',day(obs.timestamp));
  const range=player?.snapshot()||{start:0,end:timeline.observations.length-1};
  byId('previous-date').disabled=index<=range.start;byId('next-date').disabled=index>=range.end;
  document.querySelectorAll('[data-observation]').forEach(button=>{const selected=Number(button.dataset.observation)===index;button.classList.toggle('active',selected);if(selected)button.setAttribute('aria-current','date');else button.removeAttribute('aria-current');});
  byId('layer-description').textContent=description;
  byId('interval-area').textContent=interval?number(interval.candidate_area_km2):'Baseline';
  byId('interval-count').textContent=interval?interval.region_count:'—';byId('observation-valid').textContent=number(obs.valid_fraction*100,1)+'%';
  byId('interval-note').textContent=interval?(interval.region_count?`${interval.days} days between observations. These are centered-score candidates; the original pair-comparison results use their saved nominal rule.`:'No regions passed this successive centered-score rule. This does not prove no physical change or no cumulative change occurred.'):'Baseline observation; interval measurements begin at the next acquisition.';
  byId('observation-evidence').innerHTML=`${row('Timestamp UTC',obs.timestamp)}${row('Track / frame',obs.track+' / '+obs.frame)}${row('Polarization',obs.polarization)}${row('Range bandwidth',number(obs.range_bandwidth_hz/1e6,0)+' MHz')}<p class="source-id">${escaped(obs.source_granule_id)}</p><p class="caption">${escaped(obs.quality.alignment)}</p>`;
  if(model.zone)selectZone(model.zone.zone_id);highlightDate();
  byId('temporal-map').setAttribute('aria-busy','false');
}
function playbackState(state){
  const button=byId('play-dates');button.disabled=state.start===state.end;button.textContent=state.playing?'Ⅱ Pause':'▶ Play range';button.setAttribute('aria-pressed',String(state.playing));button.setAttribute('aria-label',state.playing?'Pause date playback':'Play date range');
  byId('playback-status').textContent=state.loading?'Loading saved frame…':state.playing?`Playing · ${model.displayIndex-state.start+1} / ${state.end-state.start+1} dates`:state.start===state.end?'Single acquisition selected':`Ready · ${state.end-state.start+1} saved dates`;
}
function setIndex(index){if(!player)return;const range=player.snapshot();player.seek(Math.max(range.start,Math.min(range.end,index))).catch(errorMessage);}
function setupPlayback(){
  const observations=model.timeline.observations;
  player=createPlayback({count:observations.length,initialIndex:model.index,show:async index=>{model.index=index;await renderObservation();},onState:playbackState,onError:errorMessage});
  const options=observations.map((obs,index)=>`<option value="${index}">${escaped(day(obs.timestamp))}</option>`).join('');
  byId('range-start').innerHTML=options;byId('range-end').innerHTML=options;byId('range-end').value=observations.length-1;
  for(const id of ['range-start','range-end','playback-speed','loop-dates','restart-dates'])byId(id).disabled=false;
  playbackState(player.snapshot());
}
function changeRange(changed){
  let start=Number(byId('range-start').value),end=Number(byId('range-end').value);
  if(start>end){if(changed==='start')end=start;else start=end;}
  byId('range-start').value=start;byId('range-end').value=end;player.setRange(start,end);
  byId('date-slider').min=start;byId('date-slider').max=end;
  document.querySelectorAll('[data-observation]').forEach(button=>{const index=Number(button.dataset.observation);button.disabled=index<start||index>end;});
  setIndex(start);
}
byId('date-slider').addEventListener('input',event=>setIndex(Number(event.target.value)));
byId('previous-date').addEventListener('click',()=>setIndex(model.displayIndex-1));byId('next-date').addEventListener('click',()=>setIndex(model.displayIndex+1));
byId('play-dates').addEventListener('click',()=>{if(player?.snapshot().playing)player.pause();else player?.play();});
byId('restart-dates').addEventListener('click',()=>setIndex(player.snapshot().start));
byId('range-start').addEventListener('change',()=>changeRange('start'));byId('range-end').addEventListener('change',()=>changeRange('end'));
byId('playback-speed').addEventListener('change',event=>player?.setDelay(Number(event.target.value)));
byId('loop-dates').addEventListener('change',event=>player?.setLoop(event.target.checked));
byId('zone-select').addEventListener('change',event=>{selectZone(event.target.value);highlightDate();});
for(const button of document.querySelectorAll('[data-layer]'))button.addEventListener('click',()=>{player?.pause();model.index=model.displayIndex;model.layer=button.dataset.layer;byId('context-layer').value='';document.querySelectorAll('[data-layer]').forEach(b=>b.classList.toggle('active',b===button));renderObservation().catch(errorMessage);});
byId('context-layer').addEventListener('change',event=>{model.contextLayer=event.target.value;if(!model.contextLayer)return;player?.pause();model.index=model.displayIndex;model.layer='context';document.querySelectorAll('[data-layer]').forEach(b=>b.classList.remove('active'));renderObservation().catch(errorMessage);});
document.addEventListener('visibilitychange',()=>{if(document.hidden)player?.pause();});
window.addEventListener('pagehide',()=>player?.destroy());
document.addEventListener('keydown',event=>{
  if(!player||event.repeat||event.altKey||event.ctrlKey||event.metaKey||event.target.closest('input,select,button,a,summary,[contenteditable="true"]'))return;
  if(event.code==='Space'){event.preventDefault();if(player.snapshot().playing)player.pause();else player.play();}
  if(event.target===byId('temporal-map')&&(event.key==='ArrowLeft'||event.key==='ArrowRight')){event.preventDefault();setIndex(model.displayIndex+(event.key==='ArrowLeft'?-1:1));}
});
byId('reset-view').addEventListener('click',()=>{byId('temporal-stage').style.transform='';});
byId('focus-zone').addEventListener('click',()=>{
  if(!model.zone)return;const [height,width]=model.timeline.canonical_grid.shape,a=model.timeline.canonical_grid.affine,b=model.zone.bbox_projected;
  const x=(b[0]+b[2])/2,y=(b[1]+b[3])/2,zoom=8,bound=(zoom-1)*50;
  const panX=Math.max(-bound,Math.min(bound,(.5-(x-a[2])/a[0]/width)*100*zoom));
  const panY=Math.max(-bound,Math.min(bound,(.5-(y-a[5])/a[4]/height)*100*zoom));
  byId('temporal-stage').style.transform=`translate(${panX}%,${panY}%) scale(${zoom})`;
});
try{
  const [timeline,rows,display,audit]=await Promise.all([localJson('/api/cases/nepal_case_01/timeline'),localJson(base+'zone_timeseries.json'),localJson(base+'zones_display.json'),localJson(base+'source_audit.json')]);
  model.timeline=timeline;model.rows=rows;model.display=display;
  try{
    model.context=await localJson('/api/cases/nepal_case_01/context');byId('context-layer').disabled=false;
    byId('context-provenance').innerHTML=`<p>Precipitation: NASA POWER / NASA GMAO, hourly UTC PRECTOTCORR, model/reanalysis at 0.5° × 0.625°. IMERG GIS downloads were excluded after missing-resource checks. Terrain: NASADEM HGT v001, NASA/JPL/USGS; downloaded through Microsoft Planetary Computer. Download hosts: NASA and Microsoft.</p><ul>${model.context.limitations.map(item=>`<li>${escaped(item)}</li>`).join('')}</ul>`;
  }catch{byId('context-provenance').textContent='Saved environmental context unavailable. Run make context after downloading the sources.';}

  const postEvent=timeline.observations.findIndex(o=>o.timestamp.slice(0,10)>timeline.event_reference_date);model.index=postEvent<0?0:postEvent;model.displayIndex=model.index;
  byId('series-summary').textContent=`${timeline.observations.length} compatible acquisitions · ${timeline.intervals.length} successive intervals · ${timeline.zones.length} fixed zones · track ${timeline.observations[0].track} / frame ${timeline.observations[0].frame}. ${timeline.new_folder_file_count} files in database for imp2 audited; selection details below.`;
  byId('calibration-note').textContent=`${timeline.calibration.calibration_status}: |centered MAD score| > ${timeline.calibration.threshold}. ${timeline.calibration.interpretation||'See threshold validation source.'} Causes remain UNVERIFIED.`;
  byId('reference-date').textContent='Reference date: '+day(timeline.event_reference_date+'T00:00:00Z')+' · exact onset unknown';
  byId('acquisition-buttons').innerHTML=timeline.observations.map((o,i)=>`<button data-observation="${i}">${escaped(day(o.timestamp))}<small>${number(o.valid_fraction*100,1)}% valid</small></button>`).join('');
  document.querySelectorAll('[data-observation]').forEach(button=>button.addEventListener('click',()=>setIndex(Number(button.dataset.observation))));
  byId('date-slider').max=timeline.observations.length-1;byId('date-slider').disabled=false;
  byId('zone-select').innerHTML=timeline.zones.map(z=>`<option value="${escaped(z.zone_id)}">${escaped(z.zone_id)} · ${number(z.footprint_area_km2)} km²</option>`).join('');byId('zone-select').disabled=!timeline.zones.length;
  selectZone(timeline.zones[0]?.zone_id);drawZones();
  const points=timeline.intervals.map((p,i)=>({timestamp:p.end,value:p.candidate_area_km2,index:i+1}));
  lineChart('area-chart',points,'km²',{onSelect:p=>setIndex(p.index)});
  lineChart('magnitude-chart',timeline.intervals.map(p=>({timestamp:p.end,value:p.median_absolute_change_db})),'dB');
  byId('audit-summary').textContent=`${timeline.audited_file_count} supplied HDF5 files audited, including ${timeline.new_folder_file_count} in database for imp2. ${timeline.selected_observation_count} are selected for this compatible series. Other sources remain listed with specific exclusions.`;
  byId('source-audit').innerHTML=audit.records.map(r=>`<tr><td>${escaped(r.source_file)}</td><td>${escaped(r.acquisition_start.slice(0,10))}</td><td>${r.track} / ${r.frame}</td><td>${number(r.range_bandwidth_hz/1e6,0)} MHz</td><td>${r.selected?'Selected':escaped(r.selection_reasons.join('; '))}</td></tr>`).concat(audit.unreadable_or_unsupported.map(r=>`<tr><td>${escaped(r.source_file)}</td><td>—</td><td>—</td><td>—</td><td>${escaped(r.selection_reasons.join('; '))}</td></tr>`)).join('');
  byId('temporal-method').innerHTML=`<pre>Physical quantity: ${escaped(timeline.physical_quantity)}\nZ = (successive ΔdB − median(ΔdB)) / (1.4826 × MAD + ${timeline.epsilon})\nScore cutoff: ${timeline.calibration.threshold} (${escaped(timeline.calibration.calibration_status)})\nCleanup: ${timeline.cleanup.opening_iterations} opening iteration; ${timeline.cleanup.min_region_pixels} native pixels minimum\nGrid: ${escaped(timeline.canonical_grid.crs)}, ${timeline.canonical_grid.shape.join(' × ')} pixels\nPersistence: ${escaped(timeline.persistence_definition)}\nRecovery: ${escaped(timeline.recovery_definition)}\nSource SHA-256: ${escaped(timeline.source_code_sha256)}</pre><ul>${timeline.limitations.map(item=>`<li>${escaped(item)}</li>`).join('')}</ul><p>${escaped(timeline.registration_validation)}</p>`;
  await renderObservation();setupPlayback();
  // Preload the remaining local observation previews without delaying first paint.
  for(const observation of timeline.observations)loadImage(base+observation.preview).catch(()=>{});
  if(new URLSearchParams(window.location.search).get('play')==='1')player.play();
}catch(error){errorMessage(error);}
