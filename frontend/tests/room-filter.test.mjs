import test from 'node:test';
import assert from 'node:assert/strict';
import {filterRooms} from '../src/room-filter.ts';
const rows=[{id:'a',name:'SA101',building:'A',capacity:48,type:'研讨教室',busy:[3,6],floor:1,available:true},{id:'b',name:'SB201',building:'B',capacity:80,type:'普通教室',busy:[4],floor:2},{id:'c',name:'SA102',building:'A',capacity:30,type:'普通教室',busy:[],floor:1}];
test('recalculates availability from all selected periods without trusting upstream flag',()=>{
 const result=filterRooms(rows,[3,4],'',0,'','');
 assert.deepEqual(result.map(r=>[r.id,r.available]),[['c',true],['a',false],['b',false]]);
 assert.equal(filterRooms(rows,[7],'A',40,'sa101','研讨')[0].available,true);
 assert.equal(rows[0].available,true);
});
test('combines capacity building room-name and type filters using complete snapshot',()=>{
 assert.deepEqual(filterRooms(rows,[6],'A',40,'a101','研讨').map(r=>r.id),['a']);
 assert.deepEqual(filterRooms(rows,[6],'B',90,'',''),[]);
 assert.equal(filterRooms(rows,[6],'A',0,'','普通')[0].id,'c');
});
