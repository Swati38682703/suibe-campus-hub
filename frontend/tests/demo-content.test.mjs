import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mergeDemoRows,updateDemoPatch} from '../src/demo-content-store.ts';
test('presentation edits merge by stable ID, preserve untouched fields and leave originals unchanged',()=>{
 const base=[{id:'one',title:'原始标题',source:'原文'},{id:'two',title:'另一项'}];
 const patches=updateDemoPatch([], {id:'one',title:'演示标题'});
 const rows=mergeDemoRows(base,patches);
 assert.equal(rows[0].title,'演示标题');assert.equal(rows[0].source,'原文');
 assert.equal(base[0].title,'原始标题');assert.equal(rows[1].title,'另一项');
});
test('hide and restore retain edits and do not duplicate newly created records',()=>{
 let patches=updateDemoPatch([],{id:'new',title:'新增'});
 patches=updateDemoPatch(patches,{id:'new',hidden:true});
 assert.deepEqual(mergeDemoRows([],patches),[]);
 assert.equal(mergeDemoRows([],patches,true)[0].title,'新增');
 patches=updateDemoPatch(patches,{id:'new',hidden:false});
 assert.equal(mergeDemoRows([],patches).length,1);
 assert.equal(mergeDemoRows([],patches)[0].title,'新增');
 assert.deepEqual(mergeDemoRows([{id:'original'}],[]),[{id:'original'}]);
});
