/** Logic checks with explicit DOM/terrain mocks and real saved outputs; not browser visual QA. */
import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs/promises';
import {createPlayback} from '../web/playback.mjs';
const root=new URL('../',import.meta.url),camel=key=>key.replace(/-([a-z])/g,(_,c)=>c.toUpperCase());
async function fixture(){
 const html=await fs.readFile(new URL('web/change-lab.html',root),'utf8');
 const source=(await fs.readFile(new URL('web/change-lab.mjs',root),'utf8')).replace(/^import .*;\n/gm,'');
 const elements=new Map(),nodes=[];
 function parse(text){const attrs={};for(const m of text.matchAll(/([\w:-]+)(?:="([^"]*)")?/g))attrs[m[1]]=m[2]??'';return attrs;}
 class Element{
  constructor(attrs={}){this.dataset={};this.listeners={};this.children=[];this.hidden='hidden' in attrs;this.disabled='disabled' in attrs;this.checked=false;this.value=attrs.value||'';this.attributes=attrs;this.textContent='';this.html='';const classes=new Set((attrs.class||'').split(' '));this.classList={add:v=>classes.add(v),remove:v=>classes.delete(v),contains:v=>classes.has(v),toggle:(v,yes)=>{if(yes===undefined)yes=!classes.has(v);if(yes)classes.add(v);else classes.delete(v);return yes;}};for(const [k,v] of Object.entries(attrs))if(k.startsWith('data-'))this.dataset[camel(k.slice(5))]=v;nodes.push(this);}
  set innerHTML(value){this.html=value;for(const child of this.children){const at=nodes.indexOf(child);if(at>=0)nodes.splice(at,1);}this.children=[];for(const m of value.matchAll(/<button\s+([^>]+)>/g)){const attrs=parse(m[1]);if(Object.keys(attrs).some(k=>k.startsWith('data-')))this.children.push(new Element(attrs));}}
  get innerHTML(){return this.html;}
  addEventListener(name,fn){(this.listeners[name]||=[]).push(fn);}setAttribute(k,v){this.attributes[k]=v;}removeAttribute(k){delete this.attributes[k];}
  async emit(name){for(const fn of this.listeners[name]||[])await fn({target:this});await new Promise(resolve=>setImmediate(resolve));}
  showModal(){this.open=true;}close(){this.open=false;}
 }
 for(const m of html.matchAll(/<[\w-]+\s+([^>]+)>/g)){const attrs=parse(m[1]);if(attrs.id||Object.keys(attrs).some(k=>k.startsWith('data-'))){const el=new Element(attrs);if(attrs.id)elements.set(attrs.id,el);}}
 const document={hidden:false,getElementById:id=>{assert.ok(elements.has(id),'Unknown HTML ID '+id);return elements.get(id);},querySelectorAll:selector=>{const m=selector.match(/^\[data-([\w-]+)(?:="([^"]+)")?\]$/);assert.ok(m,'Unsupported selector '+selector);return nodes.filter(n=>n.dataset[camel(m[1])]!==undefined&&(m[2]===undefined||n.dataset[camel(m[1])]===m[2]));},addEventListener(){}};
 class TerrainMock{
  constructor(canvas,mesh,options){this.mesh=mesh;this.onPick=options.onPick;this.zoom=1;}async setImages(...images){this.images=images;}draw(){}reset(){this.focused=null;}focus(tile){this.focused=tile;}setMode(mode){this.is3D=mode==='3d';return this.is3D;}
 }
 async function fetch(url){assert.ok(url.startsWith('/cases/'),'Unexpected request '+url);const data=JSON.parse(await fs.readFile(new URL('web/public'+url,root),'utf8'));return {ok:true,json:async()=>data};}
 const sandbox={console,document,window:{addEventListener(){}},fetch,TerrainView:TerrainMock,createPlayback,URLSearchParams,URL,Blob,setTimeout:()=>1,clearTimeout(){}};
 const api=await vm.runInNewContext('(async()=>{'+source+'\nreturn {state,terrain,player};})()',sandbox);
 assert.equal(elements.get('lab-error').hidden,true,elements.get('lab-error').textContent);
 return {api,elements,document};
}
test('Change Lab reads real DNA and explicitly shows censored recovery and unavailable similarity',async()=>{
 const f=await fixture();assert.equal(f.api.state.dna.zone_count,1);assert.ok(f.elements.get('dna-features').innerHTML.includes('7.53 dB'));
 assert.ok(f.elements.get('dna-censoring').innerHTML.includes('right-censored'));assert.ok(f.elements.get('dna-similar').innerHTML.includes('insufficient references'));
 assert.ok(f.elements.get('lab-validation').innerHTML.includes('INSUFFICIENT INDEPENDENT REFERENCE'));
});
test('Terrain and rainfall components switch actual saved map textures',async()=>{
 const f=await fixture();await f.document.querySelectorAll('[data-lab-layer="static"]')[0].emit('click');
 assert.ok(f.api.terrain.images[1].endsWith('landslide_static.png'));
 await f.document.querySelectorAll('[data-lab-layer="dynamic"]')[0].emit('click');assert.ok(f.api.terrain.images[1].endsWith('_dynamic.png'));
});
test('Baseline date has no radar modifier and retains its disclosed effective weights',async()=>{
 const f=await fixture();await f.document.querySelectorAll('[data-lab-date="0"]')[0].emit('click');
 assert.equal(f.api.state.index,0);assert.equal(f.document.querySelectorAll('[data-lab-layer="modifier"]')[0].disabled,true);
 const observation=f.api.state.landslide.observations[0];assert.equal(observation.component_means.nisar_modifier,null);
 assert.ok(!('nisar_modifier' in observation.effective_weights));
});
test('Guided story focuses the real zone then returns to landscape susceptibility',async()=>{
 const f=await fixture();await f.elements.get('story-next').emit('click');assert.equal(f.api.state.story,1);assert.equal(f.api.state.layer,'radar');assert.ok(f.api.terrain.focused);
 await f.elements.get('story-next').emit('click');assert.equal(f.api.state.story,2);assert.equal(f.api.state.layer,'total');assert.equal(f.api.terrain.focused,null);
 assert.ok(f.api.terrain.images[1].endsWith('_total.png'));
});
