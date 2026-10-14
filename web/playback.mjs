/** Playback of discrete saved acquisitions; waits for each frame to render. */
export function createPlayback({count,show,onState=()=>{},onError=()=>{},setTimer=setTimeout,clearTimer=clearTimeout,initialIndex=0}){
  if(!Number.isInteger(count)||count<1)throw new RangeError('Playback needs saved observations');
  let start=0,end=count-1,index=initialIndex,delay=1500,loop=false,playing=false,loading=false;
  let timer=null,epoch=0,started=false;
  const snapshot=()=>({start,end,index,delay,loop,playing,loading,count});
  const emit=()=>onState(snapshot());
  const cancelTimer=()=>{if(timer!==null)clearTimer(timer);timer=null;};
  function pause(){playing=false;loading=false;epoch++;cancelTimer();emit();}
  function schedule(token){if(playing&&token===epoch)timer=setTimer(()=>{timer=null;return advance(token);},delay);}
  async function display(target,token){
    index=target;loading=true;emit();
    try{await show(index);}
    catch(error){if(token===epoch){pause();onError(error);}return false;}
    if(token!==epoch)return false;
    loading=false;emit();return true;
  }
  async function advance(token){
    if(!playing||token!==epoch)return;
    if(index===end&&!loop){pause();return;}
    const next=index<end?index+1:start;
    if(await display(next,token))schedule(token);
  }
  async function play(){
    if(playing||start===end)return;
    playing=true;const token=++epoch;
    const target=!started||index<start||index>=end?start:index;
    started=true;
    if(await display(target,token))schedule(token);
  }
  async function seek(target){
    if(!Number.isInteger(target)||target<0||target>=count)throw new RangeError('Unknown observation');
    pause();started=true;return display(target,epoch);
  }
  function setRange(first,last){
    if(!Number.isInteger(first)||!Number.isInteger(last)||first<0||last>=count||first>last)throw new RangeError('Invalid date range');
    pause();start=first;end=last;started=false;emit();
  }
  function setDelay(value){
    if(!Number.isFinite(value)||value<100)throw new RangeError('Invalid playback speed');
    delay=value;if(timer!==null){cancelTimer();schedule(epoch);}emit();
  }
  function setLoop(value){loop=Boolean(value);emit();}
  return {play,pause,seek,setRange,setDelay,setLoop,snapshot,destroy:pause};
}
