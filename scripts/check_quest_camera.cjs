const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('camera_scan/index.html','utf8').match(/<script>([\s\S]*)<\/script>/)[1];
async function scenario(mode){
 const messages=[],events={},nodes={},stats={stopped:0,opened:0};
 for(const key of ['#video','#status','#start','#stop'])nodes[key]={style:{},textContent:'',readyState:3,play:async()=>{}};
 const parent={postMessage:m=>messages.push(m)};
 const ctx={parent,crypto:{randomUUID:()=> 'event-1'},setTimeout:()=>{},IntersectionObserver:class{observe(){}},document:{body:{scrollHeight:400},querySelector:k=>nodes[k],addEventListener:(k,f)=>events[k]=f},navigator:{mediaDevices:{getUserMedia:async()=>{stats.opened++;if(mode==='denied')throw Object.assign(new Error(),{name:'NotAllowedError'});return {getTracks:()=>[{stop:()=>stats.stopped++}]}}}}};
 ctx.window=ctx;ctx.addEventListener=(k,f)=>events[k]=f;
 if(mode!=='unsupported')ctx.BarcodeDetector=class{static async getSupportedFormats(){return ['qr_code']}async detect(){return mode==='stop'?[]:[{rawValue:'https://afjd2026.streamlit.app/?badge=p-3nm9q4'}]}};
 vm.runInNewContext(source,ctx);
 assert.equal(stats.opened,0,'never open camera before user click');
 await nodes['#start'].onclick();await new Promise(r=>setImmediate(r));
 if(mode==='ok'){
  const scans=messages.filter(m=>m.type==='streamlit:setComponentValue');assert.equal(scans.length,1);assert.equal(scans[0].value.event,'event-1');assert.equal(stats.stopped,1);assert(nodes['#video'].hidden);
 }else if(mode==='unsupported'){assert.equal(stats.opened,0);assert(nodes['#status'].textContent.includes('nicht'));}
 else if(mode==='denied'){assert(nodes['#status'].textContent.includes('nicht erlaubt'));}
 else{nodes['#stop'].onclick();assert.equal(stats.stopped,1);assert(nodes['#video'].hidden);}
}
(async()=>{for(const mode of ['ok','unsupported','denied','stop'])await scenario(mode);console.log('PASS: camera consent, decode-once, stream cleanup, denied permission and unsupported-browser fallback')})().catch(e=>{console.error(e);process.exitCode=1});

