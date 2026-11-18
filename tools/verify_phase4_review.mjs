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
 await until("document.readyState==='complete' && document.getElementById('video').readyState>=2");
 await check('one local H264/AAC video and measured phrase controls',"document.querySelectorAll('video').length===1 && document.querySelectorAll('#segments button').length===29 && document.querySelector('#video').videoWidth===1080");
 await check('technical MOCK label and no dependencies',"document.body.textContent.includes('sin voz humana') && !document.querySelector('script[src]') && !document.querySelector('link[rel=stylesheet]')");
 await evaluate("document.querySelectorAll('#segments button')[2].click()");
 await until("!document.getElementById('video').seeking && document.getElementById('video').currentTime>4");
 await delay(500);
 await check('phrase control starts playback and highlights caption',"!document.getElementById('video').paused && document.querySelector('#segments .active')!==null && document.getElementById('caption').textContent.length>0");
 await evaluate("document.getElementById('toggle').click()");
 await check('pause works',"document.getElementById('video').paused");
 await evaluate("document.getElementById('seek').value=15;document.getElementById('seek').oninput()");
 await until("!document.getElementById('video').seeking");
 await check('precise slider seek',"Math.abs(document.getElementById('video').currentTime-15)<.01");
 await evaluate("document.getElementById('home').click()");
 await until("!document.getElementById('video').seeking");
 await check('reset to start',"document.getElementById('video').paused && document.getElementById('video').currentTime===0");
 const shot=await call('Page.captureScreenshot',{format:'png'});writeFileSync(output+'/viewer-smoke.png',Buffer.from(shot.data,'base64'));
 if(errors.length)throw Error(JSON.stringify(errors));
 writeFileSync(output+'/viewer-smoke.json',JSON.stringify({pass:true,browser:'local pinned Chrome, Linux headless; Windows not directly exercised',checks,errors},null,2));
 console.log(JSON.stringify({pass:true,checks:checks.length,errors:errors.length}));
}catch(e){writeFileSync(output+'/viewer-smoke.json',JSON.stringify({pass:false,checks,errors,error:String(e)},null,2));throw e;}
finally{ws?.close();child.kill('SIGTERM');}
