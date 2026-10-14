import test from 'node:test';
import assert from 'node:assert/strict';
import {TerrainView} from '../web/terrain-view.mjs';
function plane({threeD=false,yaw=0,tilt=.68}={}){
  const view=Object.create(TerrainView.prototype);
  Object.assign(view,{gl:{},canvas:{width:1200,height:800,getBoundingClientRect:()=>({left:0,top:0,width:1200,height:800})},
    mesh:{min_elevation_m:0,width_m:24000},is3D:threeD,yaw,tilt,zoom:1,center:[0,0],exaggeration:4,
    positions:[[-1,0,-1,0,0],[1,0,-1,1,0],[-1,0,1,0,1],[1,0,1,1,1]],indices:new Uint16Array([0,2,1,1,2,3])});
  return view;
}
test('top-down center selects the center source cell',()=>{
  const point=plane().pick(600,400);assert.ok(Math.abs(point.row-400)<=1&&Math.abs(point.col-400)<=1);
});
test('northwest ground locations retain source row/column orientation',()=>{
  const view=plane(),x=(1+(-.5*.82/1.5))*600,y=(1-(.5*.82))*400,point=view.pick(x,y);
  assert.ok(Math.abs(point.row-200)<=1&&Math.abs(point.col-200)<=1);
});
test('rotated orthographic mesh picking maps back to the original geographic cell',()=>{
  const yaw=.5,tilt=.7,view=plane({threeD:true,yaw,tilt}),px=.5,pz=-.5;
  const rx=Math.cos(yaw)*px+Math.sin(yaw)*pz,rz=-Math.sin(yaw)*px+Math.cos(yaw)*pz;
  const point=view.pick((rx*.82/1.5+1)*600,(1+Math.sin(tilt)*rz*.82)*400);
  assert.ok(Math.abs(point.row-200)<=1&&Math.abs(point.col-600)<=1);
});
test('clicks outside the footprint never fabricate a cell',()=>assert.equal(plane().pick(0,0),null));
test('2D fallback accounts for the display-to-backing-store scale',()=>{
  const view=plane();view.gl=null;view.canvas.width=2400;view.canvas.height=1600;view.flatRect={x:400,y:0,side:1600};
  const point=view.pick(600,400);assert.deepEqual(point,{row:400,col:400});
});
test('keyboard navigation pans and zooms without leaving footprint limits',()=>{
 const view=plane();view.draw=()=>{};view.setAuto=()=>{};let prevented=0;
 const key=value=>view.handleKey({key:value,preventDefault:()=>prevented++});
 key('ArrowRight');assert.equal(view.center[0],.15);key('+');assert.equal(view.zoom,1.25);
 for(let i=0;i<30;i++)key('ArrowUp');assert.equal(view.center[1],-1);assert.equal(prevented,32);
});
test('keyboard Enter uses geographic picking before inspecting a cell',()=>{
 const view=plane();view.draw=()=>{};view.setAuto=()=>{};let selected=null;view.onPick=point=>selected=point;
 view.handleKey({key:'Enter',preventDefault(){}});assert.ok(Math.abs(selected.row-400)<=1);assert.ok(view.marker);
});
