import {test} from 'node:test';
import assert from 'node:assert/strict';
import {recommendFoods} from '../src/food-recommendations.ts';
const dish=(id,patch={})=>({id,name:id,restaurant:'餐厅',window:'窗口'+id,tag:'',demo:false,average:4,...patch});
const record=(id,score,tags=[])=>({id,score,tags,date:'2026-10-20'});
test('new recommendations exclude all rated or stamped dishes and demo food',()=>{
 const rows=recommendFoods([dish('old'),dish('stamp'),dish('new'),dish('demo',{demo:true})],[record('old',5)],['stamp'],'new');
 assert.deepEqual(rows.map(r=>r.dish.id),['new']);
});
test('again recommends only personal high ratings, never public scores alone',()=>{
 const rows=recommendFoods([dish('like'),dish('dislike',{average:5}),dish('unrated')],[record('like',5),record('dislike',1)],['unrated'],'again');
 assert.deepEqual(rows.map(r=>r.dish.id),['like']);assert.match(rows[0].reason,/5 星/);
});
test('preferred flavour and untried known windows affect new recommendations',()=>{
 const rows=recommendFoods([dish('old',{tag:'清淡'}),dish('mild',{tag:'清淡'}),dish('spicy',{tag:'香辣',average:5})],[record('old',5,['清淡'])],[],'new');
 assert.equal(rows[0].dish.id,'mild');assert.deepEqual(rows[0].tags,['清淡']);
});
test('unknown windows never masquerade as verified untried windows',()=>{
 const rows=recommendFoods([dish('x',{window:'窗口待核实'})],[],[],'new');
 assert.doesNotMatch(rows[0].reason,/窗口/);
});
