import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseWeeks,validateSchedule,conflicts} from '../src/api.ts';
const sample={id:'a',name:'国际贸易',teacher:'示例',room:'A101',day:1,start:3,end:4,weeks:'1-16',semester:'2026-2027-1'};
test('week ranges expand and invalid ranges are rejected',()=>{
  assert.deepEqual(parseWeeks('1-3,5'),[1,2,3,5]);
  for(const value of ['3-1','0-5','1-31','每周',''])assert.throws(()=>parseWeeks(value));
});
test('conflicts require matching semester, weekday, periods and weeks',()=>{
  assert.ok(conflicts(sample,{...sample,id:'b',start:4,end:5}));
  for(const patch of [{semester:'2026-2027-2'},{day:2},{start:5,end:6},{weeks:'17-20'}])assert.equal(conflicts(sample,{...sample,id:'b',...patch}),false);
});
test('import validates 14-period bounds and required names',()=>{
  assert.equal(validateSchedule([{...sample,end:14}])[0].end,14);
  for(const patch of [{end:15},{start:5,end:3},{day:8},{name:''},{weeks:'0-20'}])assert.throws(()=>validateSchedule([{...sample,...patch}]));
  assert.throws(()=>validateSchedule([sample,sample]));
});
