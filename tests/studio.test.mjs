/** Interaction-logic smoke tests with explicit DOM/terrain mocks, not browser or visual QA. */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs/promises';
import {createPlayback} from '../web/playback.mjs';
const root=new URL('../',import.meta.url);
async function fixture(){
  const html=await fs.readFile(new URL('web/index.html',root),'utf8');
  const source=(await fs.readFile(new URL('web/studio.mjs',root),'utf8')).replace(/^import .*;\n/gm,'');
  const elements=new Map(),nodes=[];
  class Element{
    constructor(attrs={}){this.dataset={};this.listeners={};this.children=[];this.hidden='hidden' in attrs;this.disabled='disabled' in attrs;this.checked=false;this.value=attrs.value||'';this.attributes=attrs;this.textContent='';this.html='';const classes=new Set((attrs.class||'').split(' '));this.classList={add:v=>classes.add(v),remove:v=>classes.delete(v),contains:v=>classes.has(v),toggle:(v,yes)=>{if(yes===undefined)yes=!classes.has(v);if(yes)classes.add(v);else classes.delete(v);return yes;}};for(const [key,value] of Object.entries(attrs))if(key.startsWith('data-'))this.dataset[key.slice(5)]=value;nodes.push(this);}
    set innerHTML(value){this.html=value;for(const child of this.children){const at=nodes.indexOf(child);if(at>=0)nodes.splice(at,1);}this.children=[];for(const match of value.matchAll(/<button\s+([^>]+)>/g)){const attrs=parse(match[1]);if(Object.keys(attrs).some(key=>key.startsWith('data-')))this.children.push(new Element(attrs));}}
    get innerHTML(){return this.html;}
    addEventListener(name,callback){(this.listeners[name]||=[]).push(callback);}
    setAttribute(name,value){this.attributes[name]=value;}removeAttribute(name){delete this.attributes[name];}
    async emit(name){for(const callback of this.listeners[name]||[])await callback({target:this});await new Promise(resolve=>setImmediate(resolve));}
    showModal(){this.open=true;}close(){this.open=false;}
  }
  function parse(text){const attrs={};for(const match of text.matchAll(/([\w:-]+)(?:="([^"]*)")?/g))attrs[match[1]]=match[2]??'';return attrs;}
  for(const match of html.matchAll(/<[\w-]+\s+([^>]+)>/g)){const attrs=parse(match[1]);if(attrs.id||Object.keys(attrs).some(k=>k.startsWith('data-'))){const el=new Element(attrs);if(attrs.id)elements.set(attrs.id,el);}}
  elements.get('speed').value='1500';
  const document={hidden:false,getElementById:id=>{assert.ok(elements.has(id),'Unknown HTML ID '+id);return elements.get(id);},
    querySelectorAll:selector=>{const match=selector.match(/^\[data-([\w-]+)(?:="([^"]+)")?\]$/);assert.ok(match,'Unsupported test selector '+selector);return nodes.filter(node=>node.dataset[match[1]]!==undefined&&(match[2]===undefined||node.dataset[match[1]]===match[2]));},
    querySelector(selector){return this.querySelectorAll(selector)[0];},addEventListener(){}};
  class TerrainMock{
    constructor(canvas,mesh,options){this.gl={};this.mesh=mesh;this.onPick=options.onPick;this.zoom=1;this.auto=false;}
    async setImages(...images){this.images=images;}draw(){}reset(){}focus(tile){this.focused=tile;}setAuto(value){this.auto=value;}setMode(mode){this.is3D=mode==='3d';return this.is3D;}
  }
  const expectedManifest=JSON.parse(await fs.readFile(new URL('web/public/cases/nepal_case_01/flood/manifest.json',root),'utf8'));
  const requests=[];
  async function fetch(url,options){
    if(options?.method==='POST'){
      const parameters=JSON.parse(options.body);requests.push(parameters);
      const dir=new URL('web/public/cases/nepal_case_01/flood/scenarios/',root);
      for(const name of await fs.readdir(dir)){const result=JSON.parse(await fs.readFile(new URL(name+'/result.json',dir),'utf8'));if(result.inputs_sha256===expectedManifest.inputs_sha256&&result.parameters.observation_id===parameters.observation_id&&result.parameters.rainfall_multiplier===parameters.rainfall_multiplier&&result.parameters.duration_hours===parameters.duration_hours&&result.parameters.wetness===parameters.wetness)return {ok:true,json:async()=>result};}
      throw new Error('Test requires a real precomputed scenario matching the controls');
    }
    const aliases={'/api/cases/nepal_case_01/flood-escalation':'/cases/nepal_case_01/flood/manifest.json','/api/cases/nepal_case_01/timeline':'/cases/nepal_case_01/timeseries/timeline.json','/api/cases/nepal_case_01/thermal':'/cases/nepal_case_01/thermal/manifest.json'};
    const path=aliases[url]||url;assert.ok(path.startsWith('/cases/'),'Unexpected request '+path);
    const data=JSON.parse(await fs.readFile(new URL('web/public'+path,root),'utf8'));return {ok:true,json:async()=>data};
  }
  const timers=new Map();let timerID=0;
  const sandbox={console,document,window:{matchMedia:()=>({matches:false}),addEventListener(){}},fetch,
    TerrainView:TerrainMock,createPlayback,URLSearchParams,URL,Blob,setTimeout:(fn,delay)=>{timers.set(++timerID,{fn,delay});return timerID;},clearTimeout:id=>timers.delete(id)};
  const api=await vm.runInNewContext('(async()=>{'+source+'\nreturn {state,terrain,player};})()',sandbox);
  assert.equal(elements.get('studio-error').hidden,true,elements.get('studio-error').textContent);
  return {api,elements,document,requests};
}
test('studio initializes from real saved manifests with explainable index and geographic check',async()=>{
  const {api,elements}=await fixture();assert.equal(api.state.index,2);assert.equal(elements.get('score-value').textContent,'27.3');
  assert.ok(elements.get('geography-detail').innerHTML.includes('0.000'));assert.ok(api.terrain.images[1].includes('timeseries/nisar_t3.webp'));assert.equal(elements.get('radar-panel').hidden,false);assert.equal(elements.get('evidence-panel').hidden,true);
});
test('thermal layer uses the selected real acquisition and its own coverage legend',async()=>{
  const f=await fixture();await f.document.querySelector('[data-layer="thermal"]').emit('click');
  assert.equal(f.api.state.layer,'thermal');assert.ok(f.api.terrain.images[1].endsWith(f.api.state.scene.preview));
  assert.equal(f.elements.get('legend-title').textContent,'Land surface temperature');assert.ok(f.elements.get('coverage-badge').textContent.includes('thermal'));
});
test('date selection changes map, score and independent thermal scene together',async()=>{
  const f=await fixture();await f.document.querySelector('[data-date="0"]').emit('click');
  assert.equal(f.api.state.index,0);assert.equal(f.elements.get('score-value').textContent,'20.8');assert.ok(f.api.state.scene.datetime.startsWith('2026-08-18'));
});
test('scenario controls submit the actual selected values and enable baseline comparison',async()=>{
  const f=await fixture();await f.elements.get('scenario-tab').emit('click');
  await f.document.querySelector('[data-duration="48"]').emit('click');await f.document.querySelector('[data-wetness="wet"]').emit('click');
  f.elements.get('rain-multiplier').value='1.5';await f.elements.get('rain-multiplier').emit('input');await f.elements.get('run-scenario').emit('click');
  assert.equal(f.requests.length,1);assert.equal(f.requests[0].duration_hours,48);assert.equal(f.requests[0].wetness,'wet');
  assert.equal(f.elements.get('compare-control').hidden,false);assert.equal(f.elements.get('clear-scenario').hidden,false);
  assert.ok(f.api.terrain.images[1].includes('/scenarios/'));assert.notEqual(f.api.terrain.images[1],f.api.terrain.images[2]);
  f.elements.get('compare-slider').value='30';await f.elements.get('compare-slider').emit('input');assert.equal(f.api.terrain.split,.3);
});
