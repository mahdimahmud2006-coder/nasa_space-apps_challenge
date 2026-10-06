const $ = id => document.getElementById(id);
const base = '/cases/nepal_case_01/';
const state = {manifest:null, evidence:null, pair:null, mode:'swipe', scanned:false, scanning:false, robust:false, zoom:1, panX:0, panY:0, generation:0, regions:[], nominalRegions:[], robustRegions:[], nominalOverlay:null, robustOverlay:null};
const fmt = (n,d=4) => Number(n).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
const date = s => new Date(s.endsWith('Z')?s:s+'Z').toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric',timeZone:'UTC'});
const esc = v => String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function json(url){const response=await fetch(url);if(!response.ok)throw new Error(`Local file unavailable (${response.status}): ${url}`);return response.json();}
function message(text,error=false){$('map-message').textContent=text;$('map-message').hidden=!text;$('map-message').classList.toggle('error',error);}
function resetMetrics(){for(const id of ['changed-area','region-count'])$(id).textContent='—';$('selected-region').innerHTML='<div class="section-label">REGION INSPECTOR</div><p class="muted">Scan to reveal locally computed candidates.</p>';$('sensitivity').textContent='Reveal evidence to compare ±10% cutoff.';$('validation-summary').textContent='Independent-source review appears after scanning. Radar change does not confirm a disaster.';$('histogram').replaceChildren();}
function updateSwipe(){
  const value=$('swipe-slider').value;
  $('after-image').style.clipPath=state.mode==='swipe'?`inset(0 0 0 ${value}%)`:state.mode==='after'?'none':'inset(0 100% 0 0)';
  $('swipe-line').style.left=value+'%';$('swipe-line').hidden=state.mode!=='swipe';
  $('swipe-slider').disabled=state.mode!=='swipe';
  $('before-tag').hidden=state.mode==='after';$('after-tag').hidden=state.mode==='before';
}
function setMode(mode){state.mode=mode;document.querySelectorAll('[data-mode]').forEach(button=>button.classList.toggle('active',button.dataset.mode===mode));updateSwipe();}
function applyTransform(){
  const bound=(state.zoom-1)*50;
  state.panX=Math.max(-bound,Math.min(bound,state.panX));state.panY=Math.max(-bound,Math.min(bound,state.panY));
  $('map-content').style.transform=`translate(${state.panX}%,${state.panY}%) scale(${state.zoom})`;
  $('map-viewport').classList.toggle('zoomed',state.zoom>1);
}
function setZoom(value){state.zoom=Math.max(1,Math.min(8,value));applyTransform();$('reset-view').textContent=state.zoom===1?'1:1':state.zoom.toFixed(1)+'×';$('scale-label').textContent=fmt(5/state.zoom,1)+' km';}
function histogram(distribution,threshold){
  const {counts,edges_db:edges}=distribution.histogram;const max=Math.max(...counts,1);
  $('histogram').replaceChildren();
  counts.forEach((count,i)=>{const bar=document.createElement('i');bar.style.height=Math.max(1,count/max*100)+'%';if(Math.abs((edges[i]+edges[i+1])/2)>=threshold)bar.className='tail';bar.title=`${fmt(edges[i],1)} to ${fmt(edges[i+1],1)} dB: ${count.toLocaleString()} pixels`;$('histogram').append(bar);});
}
function pathData(geometry){
  const polygons=geometry.type==='Polygon'?[geometry.coordinates]:geometry.coordinates;
  return polygons.map(polygon=>polygon.map(ring=>'M'+ring.map(c=>c.join(',')).join('L')+'Z').join('')).join('');
}
function drawRegions(){
  const svg=$('region-hits');svg.replaceChildren();
  const [height,width]=state.manifest.aoi.shape;svg.setAttribute('viewBox',`0 0 ${width} ${height}`);
  state.regions.forEach(region=>{const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',pathData(region.geometry_pixel));path.setAttribute('fill-rule','evenodd');path.dataset.regionId=region.id;path.setAttribute('role','button');path.setAttribute('tabindex','0');path.setAttribute('aria-label',`Inspect candidate region ${region.id}`);path.addEventListener('click',()=>selectRegion(region.id));path.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();selectRegion(region.id);}});svg.append(path);});
}
function displayedEvidenceRegions(){return state.robust?state.evidence.regions.filter(r=>r.robust_core):state.evidence.regions;}
function updateLayer(){
  state.regions=state.robust?state.robustRegions:state.nominalRegions;
  $('overlay-image').src=state.robust?state.robustOverlay:state.nominalOverlay;
  $('area-label').textContent=state.robust?'ROBUST CANDIDATE CORE':'NOMINAL CANDIDATE CHANGE';
  $('count-label').textContent=state.robust?'NOMINAL REGIONS WITH CORE':'CONNECTED REGIONS';
  $('count-caption').textContent=state.robust?'strict components: '+state.evidence.robust_core.connected_core_count:'after noise cleanup';
  $('changed-area').textContent=fmt(state.robust?state.evidence.robust_core.robust_area_km2:state.evidence.summary.changed_area_km2);
  $('region-count').textContent=state.robust?state.evidence.robust_core.nominal_region_count_with_core.toLocaleString():state.evidence.summary.region_count.toLocaleString();
  drawRegions();
  const candidates=displayedEvidenceRegions();
  if(candidates.length)selectRegion(candidates[0].id);
  else $('selected-region').innerHTML='<div class="section-label">REGION INSPECTOR / UNVERIFIED</div><h3 class="region-title">No retained candidates</h3><p class="muted">No connected region passes this rule. This does not establish an absence of real surface change. The −10% cutoff may retain small candidate areas.</p>';
}
function selectRegion(id){
  const region=state.evidence.regions.find(r=>r.id===id);if(!region)return;
  const temporal=region.temporal_consistency;
  const validation=region.validation||{validation_status:'UNVERIFIED',review_notes:'Independent source review pending.'};
  const core=region.robust_core;
  const coreHtml=core?`<div class="region-metric"><span>Robust core area</span><strong>${fmt(core.robust_area_km2)} km²</strong></div><p class="fine-print">${fmt(core.robust_fraction*100,1)}% of nominal region persists at +10% cutoff.</p>`:'<p class="fine-print">No pixels in this nominal region survive the +10% cutoff.</p>';
  const temporalHtml=temporal?`<div class="region-metric"><span>Temporal class</span><strong>${esc(temporal.temporal_class.replaceAll('_',' '))}</strong></div><p class="fine-print">Aug 19→31: ${fmt(temporal.t1_t2.median_delta_db,2)} dB · Aug 31→Sep 12: ${fmt(temporal.t2_t3.median_delta_db,2)} dB on these same pixels. Descriptive, not statistical.</p>`:'';
  const reviewHtml=validation.reviewed?`<p class="fine-print">${esc(validation.review_notes)} <a href="${esc(validation.source_url)}" target="_blank" rel="noreferrer">UNOSAT source ↗</a></p>`:`<p class="fine-print">${esc(validation.review_notes)}</p>`;
  $('selected-region').innerHTML=`<div class="section-label">REGION INSPECTOR / NISAR L2 GCOV PROVISIONAL</div><h3 class="region-title">Candidate region ${region.id}</h3><div class="region-metric"><span>Nominal projected area</span><strong>${fmt(region.area_km2)} km²</strong></div>${coreHtml}<div class="region-metric"><span>Median signed ΔdB</span><strong>${fmt(region.median_change_db,2)} dB</strong></div><div class="region-metric"><span>Peak |ΔdB|</span><strong>${fmt(region.peak_abs_change_db,2)} dB</strong></div>${temporalHtml}<div class="region-metric"><span>Validation</span><strong>${esc(validation.validation_status)}</strong></div>${reviewHtml}<p class="fine-print">${region.pixel_count.toLocaleString()} native grid pixels · ${fmt(region.centroid_wgs84[1],4)}° N / ${fmt(region.centroid_wgs84[0],4)}° E</p><div class="region-buttons"></div>`;
  const list=$('selected-region').querySelector('.region-buttons');
  displayedEvidenceRegions().slice(0,10).forEach(r=>{const button=document.createElement('button');button.className='region-button'+(r.id===id?' active':'');button.textContent='#'+r.id;button.title=`${fmt(r.area_km2)} km²`;button.addEventListener('click',()=>selectRegion(r.id));list.append(button);});
  const focus=document.createElement('button');focus.className='quiet-button';focus.textContent='Center on region ↗';
  focus.addEventListener('click',()=>{
    const a=state.manifest.aoi.affine,[height,width]=state.manifest.aoi.shape;
    const box=region.bbox_projected,x=(box[0]+box[2])/2,y=(box[1]+box[3])/2;
    setZoom(8);state.panX=(.5-(x-a[2])/a[0]/width)*100*state.zoom;
    state.panY=(.5-(y-a[5])/a[4]/height)*100*state.zoom;applyTransform();
  });$('selected-region').append(focus);
  document.querySelectorAll('#region-hits path').forEach(path=>path.classList.toggle('selected',Number(path.dataset.regionId)===id));
}
function reveal(){
  const evidence=state.evidence;state.scanned=true;
  $('evidence-intro').textContent='Computed radar-change candidates. Causes remain unverified.';
  $('overlay-toggle').disabled=false;$('overlay-toggle').checked=true;$('overlay-image').hidden=false;$('robust-toggle').disabled=false;
  $('download-evidence').disabled=false;
  histogram(evidence.distribution,evidence.analysis.threshold_db);
  $('sensitivity').innerHTML=Object.entries(evidence.threshold_sensitivity).map(([key,result])=>`<div class="sensitivity-row ${key==='nominal'?'nominal':''}"><span>${key==='nominal'?'Nominal':key==='lower_threshold'?'−10% cutoff':'+10% cutoff'}</span><span>${fmt(result.area_km2)} km²</span></div>`).join('');
  $('validation-summary').textContent=evidence.independent_validation?`UNOSAT mapped extent has no overlap with all ${evidence.summary.region_count} nominal regions; top 10 reviewed. Cause remains unverified.`:'Independent-source review prioritized the 24-day pair; cause remains unverified.';
  updateLayer();
  message(`${evidence.summary.region_count} candidate ${evidence.summary.region_count===1?'region':'regions'} · local processed evidence`);
  $('scan-button').innerHTML='<span>⌖</span> SCAN AGAIN <span>→</span>';
}
async function loadPair(id){
  const generation=++state.generation;state.scanned=false;state.scanning=false;state.robust=false;
  state.pair=state.manifest.pairs.find(p=>p.id===id);
  $('pair-select').value=id;$('scan-button').disabled=true;$('overlay-toggle').disabled=true;$('overlay-toggle').checked=false;$('robust-toggle').disabled=true;$('robust-toggle').checked=false;$('overlay-image').hidden=true;$('region-hits').replaceChildren();$('sweep').hidden=true;$('download-evidence').disabled=true;
  resetMetrics();setZoom(1);message('Loading local processed observations…');
  const pair=state.pair;
  const [evidence,regions,robustRegions]=await Promise.all([json(base+pair.directory+'/evidence.json'),json(base+pair.directory+'/regions_display.json'),json(base+pair.directory+'/robust_core_display.json')]);
  if(generation!==state.generation)return;
  state.evidence=evidence;state.regions=regions;state.nominalRegions=regions;state.robustRegions=robustRegions;
  const before=state.manifest.observations.find(o=>o.id===pair.before),after=state.manifest.observations.find(o=>o.id===pair.after);
  const preload=async(url)=>{const img=new Image();img.src=url;await img.decode();return url;};
  const [b,a,o,ro]=await Promise.all([preload(base+before.preview),preload(base+after.preview),preload(base+pair.directory+'/overlay.png'),preload(base+pair.directory+'/robust_core_overlay.png')]);
  if(generation!==state.generation)return;
  $('before-image').src=b;$('after-image').src=a;$('overlay-image').src=o;state.nominalOverlay=o;state.robustOverlay=ro;
  $('date-before').textContent=date(before.acquisition_start);$('date-after').textContent=date(after.acquisition_start);
  $('interval').textContent=Math.round((new Date(after.acquisition_start+'Z')-new Date(before.acquisition_start+'Z'))/86400000)+' days';
  $('pair-label').textContent=date(before.acquisition_start)+' → '+date(after.acquisition_start);
  $('before-tag').textContent='BEFORE / '+before.acquisition_start.slice(5,10);$('after-tag').textContent='AFTER / '+after.acquisition_start.slice(5,10);
  $('valid-area').textContent=fmt(evidence.summary.common_valid_area_km2,2);$('threshold').textContent=fmt(evidence.analysis.threshold_db,2);
  $('threshold-note').textContent=`${evidence.analysis.threshold_parameter} × robust MAD spread · ${evidence.analysis.cleanup.min_region_pixels} pixel minimum · ${evidence.analysis.median_filter_size} × ${evidence.analysis.median_filter_size} median filter.`;
  $('polarization').textContent=evidence.dataset.polarization;
  $('scan-button').disabled=false;$('scan-button').innerHTML='<span>⌖</span> SCAN REGION <span>→</span>';
  $('evidence-intro').textContent='Scan to reveal the computed result.';updateSwipe();message('Drag the comparison slider, then scan to reveal evidence.');renderMethods();
}
function renderMethods(){
  const e=state.evidence;if(!e)return;
  const source=e.dataset.sources.map(s=>`${s.filename}\n${s.granule_id}\n${s.acquisition_start} UTC\n${s.layer_path}\nTrack ${s.track} / frame ${s.frame} / orbit ${s.orbit} / ${s.orbit_direction}\nProduct version ${s.product_version}\nWindow SHA-256: ${s.quality.window_sha256}`).join('\n\n');
  $('methods-content').innerHTML=`<span class="badge">PROVISIONAL / CAUSE UNVERIFIED</span><h3>Measurement, not causal classification</h3><p>The map shows locally precomputed candidates from real gamma-0 radar power. The scan animation reveals saved output; it does not run science in the browser. Yellow marks increasing backscatter; blue marks decreasing backscatter.</p><h3>Sources and provenance</h3><pre>${esc(source)}</pre><p>Collection: ${esc(e.dataset.collection)} · ${esc(e.dataset.covariance_term)} / ${esc(e.dataset.polarization)} polarization. <a href="https://doi.org/10.5067/NIL2GCOV-P1" target="_blank" rel="noreferrer">NASA dataset DOI ↗</a> · <a href="https://nisar-docs.asf.alaska.edu/gcov/" target="_blank" rel="noreferrer">ASF product guide ↗</a></p><h3>Area of investigation</h3><p>${esc(e.aoi.reason)} ${esc(e.aoi.crs)}; ${e.aoi.shape.join(' × ')} native pixels. The extent is fixed across observations.</p><h3>Deterministic processing</h3><ol>${e.analysis.preprocessing.map(v=>`<li>${esc(v)}</li>`).join('')}</ol><pre>${esc(e.analysis.metric)}\n${esc(e.analysis.threshold_rule)}\nThreshold: ${fmt(e.analysis.threshold_db,4)} dB\nOpening: ${e.analysis.cleanup.opening_iterations} iteration(s), ${esc(e.analysis.cleanup.structure)}\nMinimum region: ${e.analysis.cleanup.min_region_pixels} pixels\nRanking: ${esc(e.analysis.ranking)}\nArea: ${esc(e.analysis.area_method)}\nNative pixel area: ${fmt(e.analysis.pixel_area_km2,6)} km²</pre><h3>Distribution and threshold alternatives</h3><p>Median change: ${fmt(e.distribution.median,3)} dB. MAD: ${fmt(e.distribution.mad,3)} dB. These are descriptive statistics, not significance tests.</p><table><thead><tr><th>MAD multiplier</th><th>Cutoff dB</th><th>Area km²</th><th>Regions</th></tr></thead><tbody>${e.analysis.threshold_candidates.map(v=>`<tr><td>${v.mad_multiplier}</td><td>${fmt(v.threshold_db,3)}</td><td>${fmt(v.area_km2)}</td><td>${v.region_count}</td></tr>`).join('')}</tbody></table><h3>Limitations and validation</h3><ul>${e.limitations.map(v=>`<li>${esc(v)}</li>`).join('')}</ul><h3>Reproducibility</h3><pre>${esc(JSON.stringify(e.analysis.software,null,2))}</pre><p><a href="${base+state.pair.directory}/evidence.json" download>Full evidence JSON ↓</a> · <a href="${base+state.pair.directory}/change_regions.geojson" download>Geographic region boundaries ↓</a></p>`;
}
function fail(error){console.error(error);message(error.message,true);$('scan-button').disabled=true;$('evidence-intro').textContent='Local data could not be loaded. Run make process to regenerate assets.';}
$('pair-select').addEventListener('change',event=>loadPair(event.target.value).catch(fail));
$('swipe-slider').addEventListener('input',updateSwipe);
let swipeDragging=false;
const moveSwipe=event=>{const rect=$('map-content').getBoundingClientRect();$('swipe-slider').value=Math.max(0,Math.min(100,(event.clientX-rect.left)/rect.width*100));updateSwipe();};
$('swipe-line').addEventListener('pointerdown',event=>{if(state.mode!=='swipe')return;event.stopPropagation();swipeDragging=true;event.currentTarget.setPointerCapture(event.pointerId);moveSwipe(event);});
$('swipe-line').addEventListener('pointermove',event=>{if(swipeDragging)moveSwipe(event);});
$('swipe-line').addEventListener('pointerup',()=>{swipeDragging=false;});$('swipe-line').addEventListener('pointercancel',()=>{swipeDragging=false;});
let panDrag=null;
$('map-viewport').addEventListener('pointerdown',event=>{
  if(state.zoom<=1||event.target.closest('path,.swipe-line'))return;
  panDrag={x:event.clientX,y:event.clientY,panX:state.panX,panY:state.panY};event.currentTarget.setPointerCapture(event.pointerId);
});
$('map-viewport').addEventListener('pointermove',event=>{
  if(!panDrag)return;const rect=event.currentTarget.getBoundingClientRect();
  state.panX=panDrag.panX+(event.clientX-panDrag.x)/rect.width*100;state.panY=panDrag.panY+(event.clientY-panDrag.y)/rect.height*100;applyTransform();
});
$('map-viewport').addEventListener('pointerup',()=>{panDrag=null;});$('map-viewport').addEventListener('pointercancel',()=>{panDrag=null;});
for(const button of document.querySelectorAll('[data-mode]'))button.addEventListener('click',()=>setMode(button.dataset.mode));
$('overlay-toggle').addEventListener('change',event=>{$('overlay-image').hidden=!event.target.checked;$('region-hits').hidden=!event.target.checked;});
$('robust-toggle').addEventListener('change',event=>{state.robust=event.target.checked;if(state.scanned)updateLayer();});
$('zoom-in').addEventListener('click',()=>setZoom(state.zoom*1.5));$('zoom-out').addEventListener('click',()=>setZoom(state.zoom/1.5));$('reset-view').addEventListener('click',()=>setZoom(1));
$('scan-button').addEventListener('click',async()=>{
  if(state.scanning||!state.evidence)return;state.scanning=true;const generation=state.generation;
  $('scan-button').disabled=true;$('overlay-image').hidden=true;$('region-hits').replaceChildren();$('sweep').hidden=false;
  $('sweep').style.animation='none';void $('sweep').offsetWidth;$('sweep').style.animation='';message('Revealing local processed evidence…');
  await new Promise(resolve=>setTimeout(resolve,1300));
  if(generation!==state.generation)return;$('sweep').hidden=true;state.scanning=false;$('scan-button').disabled=false;$('region-hits').hidden=false;reveal();
});
$('methods-button').addEventListener('click',()=>{$('methods-dialog').showModal();});$('close-methods').addEventListener('click',()=>$('methods-dialog').close());
$('methods-dialog').addEventListener('click',event=>{if(event.target===$('methods-dialog')){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});
$('download-evidence').addEventListener('click',()=>{const a=document.createElement('a');a.href=base+state.pair.directory+'/evidence.json';a.download=state.pair.id+'-evidence.json';a.click();});
try{
  state.manifest=await json(base+'manifest.json');
  $('observation-list').innerHTML=state.manifest.observations.map(o=>`<div class="observation"><span class="number">${esc(o.id.toUpperCase())}</span><div><time>${date(o.acquisition_start)}</time><small>${esc(o.orbit_direction.toUpperCase())} / TRACK ${o.track}</small></div></div>`).join('');
  $('pair-select').innerHTML=state.manifest.pairs.map(p=>`<option value="${esc(p.id)}">${esc(p.label)}</option>`).join('');$('pair-select').disabled=false;
  const geom=state.manifest.aoi.geometry.coordinates[0];const lon=(Math.min(...geom.map(v=>v[0]))+Math.max(...geom.map(v=>v[0])))/2,lat=(Math.min(...geom.map(v=>v[1]))+Math.max(...geom.map(v=>v[1])))/2;
  $('coordinates').textContent=`${fmt(lat,2)}° N / ${fmt(lon,2)}° E · 24 × 24 KM`;
  await loadPair(state.manifest.default_pair||state.manifest.pairs[0].id);
}catch(error){fail(error);}
