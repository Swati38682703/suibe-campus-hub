export type AgentProgress = {
 type:'status'|'tool_start'|'tool_end'|'heartbeat';
 label?:string;tool?:string;status?:'done'|'error';
};

export async function streamAgent(body:unknown, onProgress:(event:AgentProgress)=>void, signal:AbortSignal):Promise<any> {
 const controller=new AbortController();
 const abort=()=>controller.abort();
 signal.addEventListener('abort',abort,{once:true});
 if(signal.aborted)controller.abort();
 let timeoutMessage='',lastReceived=Date.now();
 const started=Date.now();
 const watchdog=setInterval(()=>{
  if(Date.now()-lastReceived>30000||Date.now()-started>250000){
   timeoutMessage='连接长时间没有响应，请检查网络后重试。';controller.abort();
  }
 },1000);
 let reader:ReadableStreamDefaultReader<Uint8Array>|undefined;
 try{
  const response=await fetch('/api/agent/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:controller.signal});
  if(!response.ok){
   let detail='';try{detail=(await response.json()).detail}catch{}
   throw new Error(typeof detail==='string'&&detail?detail:'校园助手暂时无法连接，请稍后重试。');
  }
  if(!response.body)throw new Error('浏览器未收到回答流，请稍后重试。');
  reader=response.body.getReader();
  const decoder=new TextDecoder();let buffer='';
  const consume=(line:string):{result:any}|undefined=>{
   if(!line.trim())return;
   let event:any;try{event=JSON.parse(line)}catch{throw new Error('校园助手返回了无法识别的进度，请重试。')}
   if(event.type==='result'){
    if(typeof event.result?.answer!=='string')throw new Error('校园助手未返回有效回答，请重试。');
    return {result:event.result};
   }
   if(event.type==='error')throw new Error(typeof event.message==='string'?event.message:'校园助手暂时无法完成请求。');
   if(['status','tool_start','tool_end','heartbeat'].includes(event.type))onProgress(event);
  };
  while(true){
   const {value,done}=await reader.read();
   if(value){lastReceived=Date.now();buffer+=decoder.decode(value,{stream:true})}
   if(done)buffer+=decoder.decode();
   const lines=buffer.split('\n');buffer=lines.pop()||'';
   for(const line of lines){const completed=consume(line);if(completed)return completed.result}
   if(done){
    const completed=consume(buffer);if(completed)return completed.result;
    throw new Error('连接已中断，尚未收到完整回答，请重试。');
   }
  }
 }catch(error){
  if(timeoutMessage)throw new Error(timeoutMessage);
  if(error instanceof TypeError)throw new Error('无法连接校园服务，请检查网络后重试。');
  throw error;
 }finally{
  clearInterval(watchdog);signal.removeEventListener('abort',abort);
  if(reader){try{await reader.cancel()}catch{}reader.releaseLock()}
  controller.abort();
 }
}
