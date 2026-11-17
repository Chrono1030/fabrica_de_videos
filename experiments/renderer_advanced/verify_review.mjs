import {spawn} from 'node:child_process';
import {mkdtempSync,readFileSync,existsSync,writeFileSync} from 'node:fs';
const [chrome,review,output]=process.argv.slice(2);
const profile=mkdtempSync('/tmp/fabrica-review-');
const child=spawn(chrome,['--headless','--no-sandbox','--disable-gpu','--disable-background-networking','--no-first-run','--autoplay-policy=no-user-gesture-required','--allow-file-access-from-files','--remote-debugging-address=127.0.0.1','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:'ignore'});
const delay=ms=>new Promise(r=>setTimeout(r,ms));let ws;const errors=[],checks=[];
try{
 for(let n=0;!existsSync(profile+'/DevToolsActivePort');n++){if(n>100)throw Error('Chrome did not start');await delay(100);}
 const port=readFileSync(profile+'/DevToolsActivePort','utf8').split('\n')[0];
 const pages=await(await fetch('http://127.0.0.1:'+port+'/json/list')).json();
 ws=new WebSocket(pages.find(p=>p.type==='page').webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j});
 let serial=0;const pending=new Map();ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.id){const p=pending.get(d.id);pending.delete(d.id);if(d.error)p.reject(Error(JSON.stringify(d.error)));else p.resolve(d.result);}else if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails);};
 const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++serial;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const x=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(x.exceptionDetails)throw Error(JSON.stringify(x.exceptionDetails));return x.result.value;};
 const until=async expression=>{for(let n=0;n<200;n++){if(await evaluate(expression))return;await delay(100);}throw Error('Timed out: '+expression);};
 const check=async(name,expression)=>{const actual=await evaluate(expression);if(!actual)throw Error(name+' failed');checks.push({name,pass:true});};
 await call('Runtime.enable');await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:1280,height:1100,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:'file://'+review});
 await until("document.readyState==='complete' && [...document.querySelectorAll('video')].every(v=>v.readyState>=2)");
 await check('two local H264 videos and seven scene buttons',"document.querySelectorAll('video').length===2 && document.querySelectorAll('#scenes button').length===7");
 await evaluate("document.querySelectorAll('#scenes button')[4].click()");
 await until("[...document.querySelectorAll('video')].every(v=>!v.seeking&&v.readyState>=2)");
 await check('scene seek to 28 seconds',"[...document.querySelectorAll('video')].every(v=>Math.abs(v.currentTime-28)<.001)");
 await evaluate("document.getElementById('next').click()");
 await check('one-frame step at 24 fps',"[...document.querySelectorAll('video')].every(v=>Math.abs(v.currentTime-(28+1/24))<.001)");
 await evaluate("document.getElementById('time').value=32;document.getElementById('seek').click()");
 await until("[...document.querySelectorAll('video')].every(v=>!v.seeking&&v.readyState>=2)");
 await check('seek both to same timestamp',"[...document.querySelectorAll('video')].every(v=>Math.abs(v.currentTime-32)<.001)");
 await evaluate("document.getElementById('play').click()");await delay(1200);
 await check('synchronized playback advances both',"(()=>{const v=[...document.querySelectorAll('video')];return v.every(x=>!x.paused&&x.currentTime>32.5)&&Math.abs(v[0].currentTime-v[1].currentTime)<.2})()");
 await evaluate("document.getElementById('pause').click()");
 await check('pause both',"[...document.querySelectorAll('video')].every(v=>v.paused)");
 await evaluate("document.getElementById('capture').value='32';document.getElementById('capture').onchange()");
 await until("[...document.querySelectorAll('.frames img')].every(i=>i.complete&&i.naturalWidth>0)");
 await check('matching PNG timestamps',"[...document.querySelectorAll('.frames img')].every(i=>i.src.endsWith('/run-1/frame-32.png'))");
 await evaluate("document.getElementById('run').value='2';document.getElementById('run').onchange()");
 await until("[...document.querySelectorAll('video')].every(v=>v.readyState>=2)");
 await check('second execution for both engines',"[...document.querySelectorAll('video')].every(v=>v.src.endsWith('/run-2/final.mp4'))");
 await evaluate("document.getElementById('time').value=43;document.getElementById('seek').click()");
 await until("[...document.querySelectorAll('video')].every(v=>!v.seeking&&v.readyState>=2)");
 await check('run-2 synchronized seek',"[...document.querySelectorAll('video')].every(v=>Math.abs(v.currentTime-43)<.001)");
 const shot=await call('Page.captureScreenshot',{format:'png'});writeFileSync(output+'/viewer-smoke.png',Buffer.from(shot.data,'base64'));
 if(errors.length)throw Error(JSON.stringify(errors));
 writeFileSync(output+'/viewer-smoke.json',JSON.stringify({pass:true,browser:'local pinned Chrome, Linux headless; Windows not directly exercised',checks,errors},null,2));
 console.log(JSON.stringify({pass:true,checks:checks.length,errors:errors.length}));
}catch(e){writeFileSync(output+'/viewer-smoke.json',JSON.stringify({pass:false,checks,errors,error:String(e)},null,2));throw e;}
finally{ws?.close();child.kill('SIGTERM');}
