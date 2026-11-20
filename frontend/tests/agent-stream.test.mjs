import test from 'node:test';
import assert from 'node:assert/strict';
import {streamAgent} from '../src/agent-stream.ts';

function responseFor(events){
 const bytes=new TextEncoder().encode(events.map(e=>JSON.stringify(e)).join('\n'));
 return new Response(new ReadableStream({start(c){for(let i=0;i<bytes.length;i+=2)c.enqueue(bytes.slice(i,i+2));c.close()}}));
}

test('decodes fragmented UTF-8, reports real stages, keeps answer and trace',async t=>{
 const answer={answer:'教室已找到',trace:[{tool:'find_rooms'}]};
 t.mock.method(globalThis,'fetch',async()=>responseFor([{type:'status',label:'已接收'},{type:'tool_start',tool:'find_rooms',label:'查询教室'},{type:'heartbeat'},{type:'tool_end',tool:'find_rooms',status:'done'},{type:'result',result:answer}]));
 const events=[];
 assert.deepEqual(await streamAgent({},e=>events.push(e),new AbortController().signal),answer);
 assert.deepEqual(events.map(e=>e.type),['status','tool_start','heartbeat','tool_end']);
 assert.equal(events[1].label,'查询教室');
});

test('stage reaches client while final answer is pending',async t=>{
 let push;
 const stream=new ReadableStream({start(c){push=c}});
 t.mock.method(globalThis,'fetch',async()=>new Response(stream));
 let signalProgress;
 const reported=new Promise(resolve=>{signalProgress=resolve});
 const result=streamAgent({},signalProgress,new AbortController().signal);
 const enc=new TextEncoder();
 push.enqueue(enc.encode(JSON.stringify({type:'tool_start',label:'查询教室'})+'\n'));
 await reported;
 push.enqueue(enc.encode(JSON.stringify({type:'result',result:{answer:'已完成'}})+'\n'));
 assert.equal((await result).answer,'已完成');
});

test('incomplete stream, invalid JSON, service error, and rate limit stay readable',async t=>{
 const mock=t.mock.method(globalThis,'fetch',async()=>responseFor([{type:'status',label:'等待'}]));
 await assert.rejects(streamAgent({},()=>{},new AbortController().signal),/连接已中断/);
 mock.mock.mockImplementation(async()=>new Response('not json\n'));
 await assert.rejects(streamAgent({},()=>{},new AbortController().signal),/无法识别的进度/);
 mock.mock.mockImplementation(async()=>responseFor([{type:'error',message:'模型超时'}]));
 await assert.rejects(streamAgent({},()=>{},new AbortController().signal),/模型超时/);
 mock.mock.mockImplementation(async()=>Response.json({detail:'请求过于频繁'},{status:429}));
 await assert.rejects(streamAgent({},()=>{},new AbortController().signal),/请求过于频繁/);
});

test('stop signal aborts the pending request without retrying',async t=>{
 let calls=0;
 t.mock.method(globalThis,'fetch',async(_url,{signal})=>{calls++;return await new Promise((_resolve,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('Stopped','AbortError')),{once:true}))});
 const controller=new AbortController();
 const pending=streamAgent({},()=>{},controller.signal);
 controller.abort();
 await assert.rejects(pending,{name:'AbortError'});
 assert.equal(calls,1);
});
