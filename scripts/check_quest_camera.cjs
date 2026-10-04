const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('camera_scan/index.html','utf8').match(/<script>([\s\S]*)<\/script>/)[1];
async function scenario(mode){
 const messages=[],events={},nodes={},stats={stopped:0,opened:0};
 for(const key of ['#video','#status','#start','#stop'])nodes[key]={style:{},textContent:'',readyState:3,videoWidth:640,videoHeight:480,play:async()=>{}};
 const parent={postMessage:m=>messages.push(m)};
 const ctx={parent,crypto:{randomUUID:()=> 'event-1'},setTimeout:()=>{},IntersectionObserver:class{observe(){}},document:{body:{scrollHeight:400},createElement:()=>({getContext:()=>({drawImage(){},getImageData(){return {data:new Uint8ClampedArray(4),width:1,height:1}}})}),querySelector:k=>nodes[k],addEventListener:(k,f)=>events[k]=f},navigator:{mediaDevices:{getUserMedia:async()=>{stats.opened++;if(mode==='denied')throw Object.assign(new Error(),{name:'NotAllowedError'});return {getTracks:()=>[{stop:()=>stats.stopped++}]}}}}};
 ctx.jsQR=()=>mode==='stop'?null:{data:'https://afjd2026.streamlit.app/?badge=p-3nm9q4'};
 ctx.window=ctx;ctx.addEventListener=(k,f)=>events[k]=f;
 if(mode!=='unsupported')ctx.BarcodeDetector=class{static async getSupportedFormats(){return ['qr_code']}async detect(){return mode==='stop'?[]:[{rawValue:'https://afjd2026.streamlit.app/?badge=p-3nm9q4'}]}};
 vm.runInNewContext(source,ctx);
 assert.equal(stats.opened,0,'never open camera before user click');
 await nodes['#start'].onclick();await new Promise(r=>setImmediate(r));
 if(mode==='ok'||mode==='unsupported'){
  const scans=messages.filter(m=>m.type==='streamlit:setComponentValue');assert.equal(scans.length,1);assert.equal(scans[0].value.event,'event-1');assert.equal(stats.stopped,1);assert(nodes['#video'].hidden);
 }
 else if(mode==='denied'){assert(nodes['#status'].textContent.includes('nicht erlaubt'));}
 else{nodes['#stop'].onclick();assert.equal(stats.stopped,1);assert(nodes['#video'].hidden);}
}
(async()=>{for(const mode of ['ok','unsupported','denied','stop'])await scenario(mode);console.log('PASS: camera consent, decode-once, stream cleanup, denied permission and unsupported-browser fallback')})().catch(e=>{console.error(e);process.exitCode=1});

