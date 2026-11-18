/* Pure visual components promoted from the advanced PoC's vector cards, conserved
   transfer arithmetic, counters, proportional strips and before/after comparisons.
   No editorial constants, engine API, timer, network access or provider dependency. */
window.FactoryVisuals=(()=>{
const ns='http://www.w3.org/2000/svg', clamp=v=>Math.max(0,Math.min(1,v)), smooth=v=>{v=clamp(v);return v*v*(3-2*v)};
function svg(tag,attrs={},text){const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);if(text!==undefined)e.textContent=text;return e}
function val(b,e,initial=false){const k=initial?e.initial_key:e.data_key;return k!==null&&k!==undefined?b.data[k]:(initial?e.initial_value:e.value)}
function number(v,e){if(v===null||v===undefined)return '';if(typeof v==='string')return v;const n=new Intl.NumberFormat('es-AR',{maximumFractionDigits:2}).format(v);return(e.format==='currency'?'$':'')+n+(e.format==='percent'?'%':e.unit?' '+e.unit:'')}
function text(g,s,x,y,size=34,fill){g.append(svg('text',{x,y,'font-size':size,'text-anchor':'middle',...(fill?{style:'fill:'+fill}:{})},s))}
function label(g,s,x,y,size=30,width=250){const words=s.split(/\s+/),lines=[];let line='';for(const w of words){if((line+' '+w).trim().length>Math.floor(width/(size*.53))&&line){lines.push(line);line=w}else line=(line+' '+w).trim()}if(line)lines.push(line);lines.forEach((l,j)=>text(g,l,x,y+j*size*1.18,size))}
function box(g,x,y,w,h,c){g.append(svg('rect',{x,y,width:w,height:h,rx:22,fill:c}))}
function state(scene,b,t){
 const base=scene.elements.map(e=>val(b,e)),values=base.slice(),progress=Object.fromEntries(scene.elements.map(e=>[e.id,1]));let transfer=null,focus=[],offset=scene.transition==='settle'?20*(1-smooth(t/.6)):0;
 for(const event of scene.events){const q=smooth((t-event.at)/event.duration);
  if(['grow','reveal','count','compare'].includes(event.action))event.elements.forEach(id=>progress[id]=q);
  if(event.action==='highlight'&&t>=event.at&&t<=event.at+event.duration)focus=event.elements;
  if(event.action==='transition'&&t>=event.at&&t<=event.at+event.duration)offset=20*(1-q);
  if(event.action==='transfer'){const amount=event.amount_key?b.data[event.amount_key]:event.amount,shift=Math.round(amount*q*100)/100,from=scene.elements.findIndex(e=>e.id===event.from_id),to=scene.elements.findIndex(e=>e.id===event.to_id);values[from]=base[from]-shift;values[to]=base[to]+shift;transfer={from,to,amount,q};}
 }
 return {values,progress,transfer,focus,offset};
}
function mount(root,scene,b,index){
const safe=b.safe_area,w=b.width-safe.left-safe.right,h=b.height-safe.top-safe.bottom,u=Math.min(w/920,h/1500),at=(el,x,y,width,height)=>Object.assign(el.style,{left:x+'px',top:y+'px',width:width+'px',...(height?{height:height+'px'}:{})});
root.classList.add('scene-frame');for(const [k,v] of Object.entries(b.palette))root.style.setProperty('--'+k,v);
const make=(tag,cls,value)=>{const e=document.createElement(tag);e.className=cls;if(value)e.textContent=value;root.append(e);return e};
const brand=make('div','brand',(b.source_metadata.brand||'Mente y Capital')+(b.source_metadata.currency?' · '+b.source_metadata.currency:'')+(b.source_metadata.audio_notice?' · '+b.source_metadata.audio_notice:''));at(brand,safe.left,safe.top+.01*h,w);brand.style.fontSize=28*u+'px';
const chapter=make('div','chapter',String(index+1).padStart(2,'0')+' / '+String(b.scenes.length).padStart(2,'0'));at(chapter,safe.left,safe.top+.01*h,w);chapter.style.fontSize=28*u+'px';
const heading=make('h1','title',scene.title);at(heading,safe.left,safe.top+.06*h,w,.14*h);heading.style.fontSize=(b.typography.heading_px||68)*u+'px';
const graph=svg('svg',{viewBox:'0 0 920 760',class:'visual'});at(graph,safe.left,safe.top+.23*h,w,.46*h);root.append(graph);
const narrative=make('p','narrative',b.source_metadata.narrative_mode==='burned_subtitles'?'':scene.narrative);at(narrative,safe.left,safe.top+.70*h,w,.22*h);narrative.style.fontSize=(b.typography.body_px||40)*u+'px';narrative.dataset.segment=scene.narrative_segment_id;
const disclaimer=make('div','disclaimer',b.source_metadata.disclaimer||'');at(disclaimer,safe.left,safe.top+.94*h,w,.05*h);disclaimer.style.fontSize=26*u+'px';
const progress=make('div','progress');at(progress,safe.left,safe.top+h-6*u,w,4*u);const ink=document.createElement('i');progress.append(ink);
const old=scene.elements.map(e=>val(b,e,true));
function frame(t){const current=state(scene,b,t),values=current.values,transfer=current.transfer;graph.style.transform=`translateY(${current.offset}px)`;graph.replaceChildren();const color=e=>current.focus.length?(current.focus.includes(e.id)?b.palette.gold:b.palette.muted):b.palette[e.color_role];
const gold=b.palette.gold,muted=b.palette.muted,surface=b.palette.surface,n=values.length;
if(scene.layout==='counter'){
 scene.elements.forEach((e,j)=>{const p=current.progress[e.id],v=typeof values[j]==='number'?values[j]*p:values[j];text(graph,number(v,e),460,235+j*240,Math.min(112,920/Math.max(8,number(v,e).length)*1.3),gold);label(graph,e.label,460,305+j*240,38,850)});
}else if(['distribution','transfer'].includes(scene.layout)){
 const total=values.reduce((a,v)=>a+v,0);let x=40;
 scene.elements.forEach((e,j)=>{const p=current.progress[e.id],width=840*values[j]/total;graph.append(svg('rect',{x,y:120,width,height:140,opacity:p,fill:color(e)}));x+=width;
 const cx=460+(j-(n-1)/2)*(860/n);box(graph,cx-410/n,360,820/n,230,surface);label(graph,e.label,cx,410,28,780/n);text(graph,number(values[j],e),cx,515,Math.min(42,760/n/number(values[j],e).length*1.5));text(graph,new Intl.NumberFormat('es-AR',{maximumFractionDigits:1}).format(100*values[j]/total)+'%',cx,565,28,muted)});
 if(scene.caption)label(graph,scene.caption,460,55,30,850);
 if(transfer){const from=460+(transfer.from-(n-1)/2)*(860/n),to=460+(transfer.to-(n-1)/2)*(860/n);graph.append(svg('path',{d:`M${from} 610 Q${(from+to)/2} 705 ${to} 610`,fill:'none',stroke:gold,'stroke-width':5}));const f=transfer.q;graph.append(svg('circle',{cx:from+(to-from)*f,cy:610+190*f*(1-f),r:17,fill:gold}));text(graph,number(transfer.amount,scene.elements[transfer.from]),460,735,40,gold)}
}else if(scene.layout==='bars'||(scene.layout==='comparison'&&values.every(v=>typeof v==='number'))){
 const max=Math.max(1,...values,...old.filter(v=>typeof v==='number'));const row=640/n;
 scene.elements.forEach((e,j)=>{const p=current.progress[e.id],y=70+j*row,previous=old[j];label(graph,e.label,460,y,32,850);box(graph,70,y+35,780,Math.min(60,row*.24),surface);
 if(typeof previous==='number')graph.append(svg('rect',{x:70,y:y+35,width:780*previous/max,height:Math.min(60,row*.24),fill:muted,opacity:.45}));
 graph.append(svg('rect',{x:70,y:y+35,width:780*values[j]/max*p,height:Math.min(60,row*.24),fill:color(e)}));text(graph,(typeof previous==='number'?number(previous,e)+' → ':'')+number(values[j],e),460,y+Math.min(120,row*.65),38)});
}else{
 const cols=scene.layout==='flow'?1:Math.min(2,n),rows=Math.ceil(n/cols),cw=840/cols,rh=660/rows;
 scene.elements.forEach((e,j)=>{const p=current.progress[e.id],x=40+(j%cols)*cw,y=35+Math.floor(j/cols)*rh,delay=n>1?j*.12:0,opacity=clamp((p-delay)/(1-delay));const g=svg('g',{opacity,transform:`translate(0 ${(1-opacity)*25})`});
 box(g,x+12,y,cw-24,rh-35,surface);g.lastChild.setAttribute('stroke',color(e));g.lastChild.setAttribute('stroke-width','2');label(g,e.label,x+cw/2,y+(values[j]===null||values[j]===undefined?rh*.43:rh*.30),n<=2?42:34,cw-70);if(values[j]!==null&&values[j]!==undefined)text(g,number(values[j],e),x+cw/2,y+rh*.70,46,gold);graph.append(g);
 if(scene.layout==='flow'&&j<n-1)graph.append(svg('path',{d:`M460 ${y+rh-35}v35`,stroke:gold,'stroke-width':5,opacity}));});
}
ink.style.transform=`scaleX(${(scene.start+t)/b.duration})`;}
return frame;
}
return {mount,number,state};
})();
