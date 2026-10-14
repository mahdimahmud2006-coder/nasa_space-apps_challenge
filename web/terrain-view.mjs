/** Local NASADEM height mesh; WebGL display only, never scientific computation. */
export class TerrainView{
  constructor(canvas,mesh,{onPick=()=>{},onStatus=()=>{}}={}){
    this.canvas=canvas;this.mesh=mesh;this.onPick=onPick;this.onStatus=onStatus;
    this.yaw=-.35;this.tilt=.68;this.zoom=1;this.exaggeration=4;this.center=[0,0];this.is3D=true;this.auto=false;this.split=1;this.opacity=.83;this.marker=null;this.tile=null;this.images={};this.frame=null;
    this.gl=canvas.getContext('webgl',{alpha:false,antialias:true});
    if(this.gl){try{this.initGL();}catch{const fallback=canvas.cloneNode();canvas.replaceWith(fallback);canvas=fallback;this.canvas=fallback;this.gl=null;}}
    if(!this.gl){this.context=canvas.getContext('2d');this.is3D=false;onStatus('2D fallback · WebGL unavailable');}
    this.observer=new ResizeObserver(()=>this.resize());this.observer.observe(canvas);
    let drag=null;
    canvas.addEventListener('pointerdown',event=>{if(event.button!==0)return;this.auto=false;drag={x:event.clientX,y:event.clientY,oldX:event.clientX,oldY:event.clientY,moved:false};canvas.setPointerCapture(event.pointerId);});
    canvas.addEventListener('pointermove',event=>{if(!drag)return;const dx=event.clientX-drag.oldX,dy=event.clientY-drag.oldY;if(Math.hypot(event.clientX-drag.x,event.clientY-drag.y)>4)drag.moved=true;if(drag.moved&&this.is3D){this.yaw+=dx*.007;this.tilt=Math.max(.12,Math.min(1.25,this.tilt+dy*.006));this.draw();}drag.oldX=event.clientX;drag.oldY=event.clientY;});
    canvas.addEventListener('pointerup',event=>{if(drag&&!drag.moved){const point=this.pick(event.clientX,event.clientY);if(point){this.marker=[point.col/800,point.row/800];this.draw();onPick(point);}}drag=null;});
    canvas.addEventListener('pointercancel',()=>{drag=null;});
    canvas.addEventListener('keydown',event=>this.handleKey(event));
    canvas.addEventListener('wheel',event=>{if(!event.ctrlKey&&!event.metaKey)return;event.preventDefault();this.zoom=Math.max(.7,Math.min(4,this.zoom*Math.exp(-event.deltaY*.002)));this.draw();},{passive:false});
    document.addEventListener('visibilitychange',()=>{if(document.hidden)this.setAuto(false);});this.resize();
  }
  initGL(){
    const gl=this.gl;
    const vertex=`attribute vec3 aPosition;attribute vec2 aUV;attribute vec3 aNormal;uniform float uYaw,uTilt,uScale,uAspect,uHeightScale,uMin;uniform vec2 uCenter;varying vec2 vUV;varying vec3 vNormal;
      void main(){vec3 p=vec3(aPosition.x-uCenter.x,(aPosition.y-uMin)*uHeightScale,aPosition.z-uCenter.y);float x=cos(uYaw)*p.x+sin(uYaw)*p.z;float z=-sin(uYaw)*p.x+cos(uYaw)*p.z;float y=cos(uTilt)*p.y-sin(uTilt)*z;float d=sin(uTilt)*p.y+cos(uTilt)*z;gl_Position=vec4(x*uScale/uAspect,y*uScale,-d*.15,1.);vUV=aUV;vNormal=normalize(vec3(aNormal.x*uHeightScale*12000.,aNormal.y,aNormal.z*uHeightScale*12000.));}`;
    const fragment=`precision mediump float;uniform sampler2D uBase,uLayer,uBefore;uniform float uOpacity,uSplit;uniform vec2 uMarker;uniform vec4 uTile;uniform float uThreeD;varying vec2 vUV;varying vec3 vNormal;
      void main(){vec4 base=texture2D(uBase,vUV);vec4 layer=vUV.x<uSplit?texture2D(uBefore,vUV):texture2D(uLayer,vUV);vec3 color=mix(base.rgb,layer.rgb,layer.a*uOpacity);if(layer.a<.1&&uOpacity>.1){float stripe=step(.5,fract((gl_FragCoord.x+gl_FragCoord.y)/13.));color=mix(base.rgb,vec3(.20,.25,.27),.45+stripe*.2);}float light=.72+.28*max(0.,dot(normalize(vNormal),normalize(vec3(-.5,1.,-.4))));color*=mix(1.,light,uThreeD);float marker=abs(distance(vUV,uMarker)-.008);if(uMarker.x>=0.&&marker<.0016)color=vec3(.97,.98,.88);if(uTile.x>=0.&&vUV.x>=uTile.x&&vUV.x<=uTile.z&&vUV.y>=uTile.y&&vUV.y<=uTile.w){float edge=min(min(vUV.x-uTile.x,uTile.z-vUV.x),min(vUV.y-uTile.y,uTile.w-vUV.y));if(edge<.0018)color=vec3(.98,.88,.61);}gl_FragColor=vec4(color,1.);}`;
    const compile=(type,source)=>{const shader=gl.createShader(type);gl.shaderSource(shader,source);gl.compileShader(shader);if(!gl.getShaderParameter(shader,gl.COMPILE_STATUS))throw new Error('Terrain shader could not compile');return shader;};
    const program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,vertex));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragment));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw new Error('Terrain display could not initialize');gl.useProgram(program);this.program=program;
    const rows=this.mesh.heights_m.length,cols=this.mesh.heights_m[0].length,vertices=new Float32Array(rows*cols*8),indices=[];this.positions=[];
    for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
      const h=this.mesh.heights_m[r][c],x=c/(cols-1)*2-1,z=r/(rows-1)*2-1;
      const dx=(this.mesh.heights_m[r][Math.min(cols-1,c+1)]-this.mesh.heights_m[r][Math.max(0,c-1)])/(c===0||c===cols-1?this.mesh.spacing_m:2*this.mesh.spacing_m);
      const dz=(this.mesh.heights_m[Math.min(rows-1,r+1)][c]-this.mesh.heights_m[Math.max(0,r-1)][c])/(r===0||r===rows-1?this.mesh.spacing_m:2*this.mesh.spacing_m);
      vertices.set([x,h,z,c/(cols-1),r/(rows-1),-dx,1,-dz],(r*cols+c)*8);this.positions.push([x,h,z,c/(cols-1),r/(rows-1)]);
      if(r<rows-1&&c<cols-1){const i=r*cols+c;indices.push(i,i+cols,i+1,i+1,i+cols,i+cols+1);}
    }
    this.indices=new Uint16Array(indices);this.count=indices.length;
    const buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,vertices,gl.STATIC_DRAW);
    for(const [name,size,offset] of [['aPosition',3,0],['aUV',2,12],['aNormal',3,20]]){const loc=gl.getAttribLocation(program,name);gl.enableVertexAttribArray(loc);gl.vertexAttribPointer(loc,size,gl.FLOAT,false,32,offset);}
    const elements=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,elements);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,this.indices,gl.STATIC_DRAW);
    this.uniforms={};for(const key of ['uYaw','uTilt','uScale','uAspect','uHeightScale','uMin','uCenter','uOpacity','uSplit','uMarker','uTile','uThreeD'])this.uniforms[key]=gl.getUniformLocation(program,key);
    this.textures={};for(const [index,key] of ['uBase','uLayer','uBefore'].entries()){
      const texture=gl.createTexture();gl.activeTexture(gl.TEXTURE0+index);gl.bindTexture(gl.TEXTURE_2D,texture);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,1,1,0,gl.RGBA,gl.UNSIGNED_BYTE,new Uint8Array([23,39,44,255]));
      gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.uniform1i(gl.getUniformLocation(program,key),index);this.textures[key]={texture,index};
    }
    gl.enable(gl.DEPTH_TEST);gl.clearColor(.035,.065,.083,1);
  }
  async setImages(base,layer=base,before=layer){
    const token=this.imageToken=(this.imageToken||0)+1;
    const load=url=>{if(this.images[url])return this.images[url];const img=new Image();img.src=url;return this.images[url]=img.decode().then(()=>img).catch(error=>{delete this.images[url];throw error;});};
    const result=await Promise.all([load(base),load(layer),load(before)]);if(token!==this.imageToken)return;
    this.currentImages=result;
    if(this.gl){for(const [i,key] of ['uBase','uLayer','uBefore'].entries()){const item=this.textures[key];this.gl.activeTexture(this.gl.TEXTURE0+item.index);this.gl.bindTexture(this.gl.TEXTURE_2D,item.texture);this.gl.texImage2D(this.gl.TEXTURE_2D,0,this.gl.RGBA,this.gl.RGBA,this.gl.UNSIGNED_BYTE,result[i]);}}
    this.draw();
  }
  resize(){const box=this.canvas.getBoundingClientRect(),ratio=Math.min(window.devicePixelRatio||1,2);this.canvas.width=Math.max(1,Math.round(box.width*ratio));this.canvas.height=Math.max(1,Math.round(box.height*ratio));this.draw();}
  draw(){
    if(!this.canvas.width||!this.canvas.height)return;
    this.projected=null;
    if(!this.gl){this.draw2D();return;}
    const gl=this.gl;gl.viewport(0,0,this.canvas.width,this.canvas.height);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.useProgram(this.program);
    const values={uYaw:this.is3D?this.yaw:0,uTilt:this.is3D?this.tilt:Math.PI/2,uScale:.82*this.zoom,uAspect:this.canvas.width/this.canvas.height,uHeightScale:this.is3D?this.exaggeration*2/this.mesh.width_m:0,uMin:this.mesh.min_elevation_m,uOpacity:this.opacity,uSplit:this.split,uThreeD:this.is3D?1:0};
    // Top-down uses a 90-degree rotation: y = -north/south coordinate.
    for(const [key,value] of Object.entries(values))gl.uniform1f(this.uniforms[key],value);
    gl.uniform2fv(this.uniforms.uCenter,this.center);gl.uniform2fv(this.uniforms.uMarker,this.marker||[-1,-1]);gl.uniform4fv(this.uniforms.uTile,this.tile||[-1,-1,-1,-1]);gl.drawElements(gl.TRIANGLES,this.count,gl.UNSIGNED_SHORT,0);
  }
  draw2D(){
    const ctx=this.context;if(!ctx)return;const w=this.canvas.width,h=this.canvas.height;ctx.fillStyle='#09151b';ctx.fillRect(0,0,w,h);if(!this.currentImages)return;
    const side=Math.min(w,h)*.82*this.zoom,x=(w-side)/2-this.center[0]*side/2,y=(h-side)/2-this.center[1]*side/2;this.flatRect={x,y,side};
    const [base,layer,before]=this.currentImages;ctx.drawImage(base,x,y,side,side);ctx.globalAlpha=this.opacity;
    const draw=image=>{ctx.drawImage(image,x,y,side,side);if(this.opacity>.1){if(!this.gapMasks)this.gapMasks=new WeakMap();if(!this.gapMasks.has(image)){const mask=document.createElement('canvas');mask.width=image.naturalWidth;mask.height=image.naturalHeight;const mc=mask.getContext('2d');mc.drawImage(image,0,0);mc.globalCompositeOperation='source-out';const tile=document.createElement('canvas');tile.width=12;tile.height=12;const tc=tile.getContext('2d');tc.fillStyle='#354047cc';tc.fillRect(0,0,12,12);tc.strokeStyle='#7c8e9488';tc.lineWidth=2;tc.beginPath();tc.moveTo(-3,12);tc.lineTo(12,-3);tc.moveTo(9,15);tc.lineTo(15,9);tc.stroke();mc.fillStyle=mc.createPattern(tile,'repeat');mc.fillRect(0,0,mask.width,mask.height);this.gapMasks.set(image,mask);}ctx.drawImage(this.gapMasks.get(image),x,y,side,side);}};
    ctx.save();ctx.beginPath();ctx.rect(x,y,side*this.split,side);ctx.clip();draw(before);ctx.restore();ctx.save();ctx.beginPath();ctx.rect(x+side*this.split,y,side*(1-this.split),side);ctx.clip();draw(layer);ctx.restore();ctx.globalAlpha=1;
    if(this.tile){ctx.strokeStyle='#fae19b';ctx.lineWidth=2;ctx.strokeRect(x+this.tile[0]*side,y+this.tile[1]*side,(this.tile[2]-this.tile[0])*side,(this.tile[3]-this.tile[1])*side);}
    if(this.marker){ctx.beginPath();ctx.arc(x+this.marker[0]*side,y+this.marker[1]*side,6,0,Math.PI*2);ctx.strokeStyle='#fff2b0';ctx.lineWidth=2;ctx.stroke();}
  }
  pick(clientX,clientY){
    const box=this.canvas.getBoundingClientRect();
    if(!this.gl){const r=this.flatRect;if(!r)return null;const x=(clientX-box.left)*this.canvas.width/box.width,y=(clientY-box.top)*this.canvas.height/box.height;const u=(x-r.x)/r.side,v=(y-r.y)/r.side;return u>=0&&u<=1&&v>=0&&v<=1?{row:Math.min(799,Math.floor(v*800)),col:Math.min(799,Math.floor(u*800))}:null;}
    const x=(clientX-box.left)/box.width*2-1,y=1-(clientY-box.top)/box.height*2;
    if(!this.projected){const yaw=this.is3D?this.yaw:0,tilt=this.is3D?this.tilt:Math.PI/2,aspect=this.canvas.width/this.canvas.height,scale=.82*this.zoom;this.projected=this.positions.map(p=>{
      const px=p[0]-this.center[0],pz=p[2]-this.center[1],h=this.is3D?(p[1]-this.mesh.min_elevation_m)*this.exaggeration*2/this.mesh.width_m:0;
      const rx=Math.cos(yaw)*px+Math.sin(yaw)*pz,rz=-Math.sin(yaw)*px+Math.cos(yaw)*pz;
      return [rx*scale/aspect,(Math.cos(tilt)*h-Math.sin(tilt)*rz)*scale,-(Math.sin(tilt)*h+Math.cos(tilt)*rz)*.15,p[3],p[4]];
    });}
    let closest=Infinity,hit=null;
    for(let i=0;i<this.indices.length;i+=3){const a=this.projected[this.indices[i]],b=this.projected[this.indices[i+1]],c=this.projected[this.indices[i+2]];
      const d=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1]);if(Math.abs(d)<1e-10)continue;
      const u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/d,v=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/d,t=1-u-v;
      if(u<0||v<0||t<0)continue;const depth=u*a[2]+v*b[2]+t*c[2];if(depth>=closest)continue;closest=depth;
      hit={col:Math.max(0,Math.min(799,Math.floor((u*a[3]+v*b[3]+t*c[3])*800))),row:Math.max(0,Math.min(799,Math.floor((u*a[4]+v*b[4]+t*c[4])*800)))};
    }return hit;
  }
  setMode(mode){this.is3D=mode==='3d'&&Boolean(this.gl);this.setAuto(false);this.draw();return this.is3D;}
  handleKey(event){
    const step=.15/this.zoom;
    if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-','Enter','Escape'].includes(event.key)){
      event.preventDefault();this.setAuto(false);
      if(event.key==='ArrowLeft')this.center[0]=Math.max(-1,this.center[0]-step);
      if(event.key==='ArrowRight')this.center[0]=Math.min(1,this.center[0]+step);
      if(event.key==='ArrowUp')this.center[1]=Math.max(-1,this.center[1]-step);
      if(event.key==='ArrowDown')this.center[1]=Math.min(1,this.center[1]+step);
      if(event.key==='+'||event.key==='=')this.zoom=Math.min(4,this.zoom*1.25);
      if(event.key==='-')this.zoom=Math.max(.7,this.zoom/1.25);
      if(event.key==='Escape'){this.reset();return;}
      this.draw();
      if(event.key==='Enter'){
        const box=this.canvas.getBoundingClientRect(),point=this.pick(box.left+box.width/2,box.top+box.height/2);
        if(point){this.marker=[point.col/800,point.row/800];this.draw();this.onPick(point);}
      }
    }
  }
  setAuto(value){this.auto=Boolean(value)&&this.is3D;if(this.frame!==null)cancelAnimationFrame(this.frame);this.frame=null;if(this.auto){let previous=performance.now();const tick=now=>{if(!this.auto)return;this.yaw+=(now-previous)*.00008;previous=now;this.draw();this.frame=requestAnimationFrame(tick);};this.frame=requestAnimationFrame(tick);}}
  reset(){this.zoom=1;this.center=[0,0];this.yaw=-.35;this.tilt=.68;this.tile=null;this.marker=null;this.draw();}
  focus(tile){this.center=[(tile.col_start+tile.width/2)/800*2-1,(tile.row_start+tile.height/2)/800*2-1];this.zoom=2.2;this.tile=[tile.col_start/800,tile.row_start/800,(tile.col_start+tile.width)/800,(tile.row_start+tile.height)/800];this.draw();}
}
