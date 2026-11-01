import test from 'node:test';
import assert from 'node:assert/strict';
import {api} from '../src/api.ts';
test('empty proxy failures display a service error instead of a JSON parsing exception',async t=>{
 t.mock.method(globalThis,'fetch',async()=>new Response('',{status:500}));
 await assert.rejects(api('/agent/chat'),/校园服务暂时无法连接/);
});
test('HTML gateway failures never expose a JSON parser error',async t=>{
 t.mock.method(globalThis,'fetch',async()=>new Response('<h1>Bad gateway</h1>',{status:502}));
 await assert.rejects(api('/agent/chat'),/校园服务暂时无法连接/);
});
test('backend details survive, including model service failures',async t=>{
 t.mock.method(globalThis,'fetch',async()=>Response.json({detail:'校园智能体服务暂不可用'},{status:503}));
 await assert.rejects(api('/agent/chat'),/校园智能体服务暂不可用/);
});
test('empty success responses are rejected while 204 stays valid',async t=>{
 const fetch=t.mock.method(globalThis,'fetch',async()=>new Response('',{status:200}));
 await assert.rejects(api('/agent/chat'),/返回了空内容/);
 fetch.mock.mockImplementation(async()=>new Response(null,{status:204}));
 assert.equal(await api('/reviews/id'),null);
});
test('network failure is readable and valid JSON answers remain intact',async t=>{
 const fetch=t.mock.method(globalThis,'fetch',async()=>{throw new TypeError('Failed to fetch')});
 await assert.rejects(api('/agent/chat'),/无法连接校园服务/);
 fetch.mock.mockImplementation(async()=>Response.json({answer:'已找到报修入口'}));
 assert.deepEqual(await api('/agent/chat'),{answer:'已找到报修入口'});
});
