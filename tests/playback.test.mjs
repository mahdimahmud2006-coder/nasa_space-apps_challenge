import test from 'node:test';
import assert from 'node:assert/strict';
import {createPlayback} from '../web/playback.mjs';

function fixture(options={}){
  const timers=new Map(),frames=[],errors=[],states=[];let id=0;
  const player=createPlayback({count:3,show:async index=>{frames.push(index);},
    onState:state=>states.push(state),onError:error=>errors.push(error),
    setTimer:(fn,delay)=>{timers.set(++id,{fn,delay});return id;},clearTimer:key=>timers.delete(key),...options});
  async function tick(){const entry=timers.entries().next().value;assert.ok(entry,'Expected a scheduled frame');timers.delete(entry[0]);await entry[1].fn();}
  return {player,timers,frames,errors,states,tick};
}

test('first play traverses the whole saved range, even when initial view is in its middle',async()=>{
  const f=fixture({initialIndex:1});await f.player.play();assert.deepEqual(f.frames,[0]);
  await f.tick();await f.tick();assert.deepEqual(f.frames,[0,1,2]);
  await f.tick();assert.equal(f.player.snapshot().playing,false);assert.equal(f.timers.size,0);
  await f.player.play();assert.deepEqual(f.frames,[0,1,2,0]);
});
test('pause cancels the timer and prevents an already queued callback advancing',async()=>{
  const f=fixture();await f.player.play();const queued=[...f.timers.values()][0].fn;
  f.player.pause();await queued();assert.deepEqual(f.frames,[0]);assert.equal(f.timers.size,0);
});
test('loop returns to range start without introducing intermediate dates',async()=>{
  const f=fixture();f.player.setRange(1,2);f.player.setLoop(true);await f.player.play();
  await f.tick();await f.tick();assert.deepEqual(f.frames,[1,2,1]);assert.equal(f.player.snapshot().playing,true);f.player.pause();
});
test('manual seek pauses playback, then play resumes the selected acquisition',async()=>{
  const f=fixture();await f.player.play();await f.player.seek(1);assert.equal(f.timers.size,0);
  assert.equal(f.player.snapshot().playing,false);await f.player.play();await f.tick();
  assert.deepEqual(f.frames,[0,1,1,2]);
});
test('a new range resets playback and a single-date range cannot autoplay',async()=>{
  const f=fixture();await f.player.play();f.player.setRange(1,2);assert.equal(f.timers.size,0);
  await f.player.play();assert.equal(f.frames.at(-1),1);
  f.player.setRange(2,2);await f.player.play();assert.equal(f.player.snapshot().playing,false);
});
test('slow image loading completes before the next frame timer starts',async()=>{
  let release;const pending=new Promise(resolve=>release=resolve);
  const f=fixture({show:()=>pending});const playing=f.player.play();
  assert.equal(f.player.snapshot().loading,true);assert.equal(f.timers.size,0);
  release();await playing;assert.equal(f.player.snapshot().loading,false);assert.equal(f.timers.size,1);
});
test('pause and seek during a pending frame cannot restart its old playback',async()=>{
  let release;const pending=new Promise(resolve=>release=resolve);
  const f=fixture({show:index=>index===0?pending:Promise.resolve()});const playing=f.player.play();
  await f.player.seek(1);release();await playing;
  assert.equal(f.player.snapshot().index,1);assert.equal(f.player.snapshot().playing,false);assert.equal(f.timers.size,0);
});
test('load failure stops playback and reports the error without another timer',async()=>{
  const error=new Error('Missing local image');const f=fixture({show:async()=>{throw error;}});
  await f.player.play();assert.deepEqual(f.errors,[error]);assert.equal(f.timers.size,0);
  assert.equal(f.player.snapshot().playing,false);
});
test('speed changes reschedule a waiting timer and preserve the current frame',async()=>{
  const f=fixture();await f.player.play();f.player.setDelay(750);
  assert.equal(f.timers.size,1);assert.equal([...f.timers.values()][0].delay,750);assert.deepEqual(f.frames,[0]);
  await f.tick();assert.deepEqual(f.frames,[0,1]);
});
test('invalid range, speed and frame positions are rejected',async()=>{
  const f=fixture();assert.throws(()=>f.player.setRange(2,1),RangeError);
  assert.throws(()=>f.player.setRange(-1,2),RangeError);assert.throws(()=>f.player.setDelay(0),RangeError);
  await assert.rejects(f.player.seek(3),RangeError);
});
