import {test} from 'node:test';
import assert from 'node:assert/strict';
import {COMPETITIONS,shanghaiDay,competitionStatus,daysBetween,deadlineICS} from '../src/competitions-data.ts';
const event=COMPETITIONS.find(c=>c.id==='market-17');
test('competition status respects expiry and freshness, not computer timezone',()=>{
 assert.equal(shanghaiDay(new Date('2026-10-30T16:01:00Z')),'2026-10-31');
 assert.equal(competitionStatus({...event,checked:'2026-10-31'},'2026-10-31'),'open');
 assert.equal(competitionStatus({...event,checked:'2026-10-31'},'2026-11-01'),'closed');
 assert.equal(competitionStatus(event,'2026-10-24'),'unknown');
 assert.equal(competitionStatus({...event,registrationStart:'2026-10-20'},'2026-10-16'),'upcoming');
 assert.equal(competitionStatus(COMPETITIONS.find(c=>c.id==='mcm-2027'),'2026-10-16'),'unknown');
 assert.equal(competitionStatus(COMPETITIONS.find(c=>c.id==='suibe-ecommerce-16'),'2026-10-16'),'closed');
 assert.equal(daysBetween('2026-12-31','2027-01-01'),1);
});
test('deadline calendar uses an exclusive end date and folds UTF8 safely',()=>{
 const output=deadlineICS(event),unfolded=output.replace(/\r\n /g,'');
 assert.ok(unfolded.includes('DTSTART;VALUE=DATE:20261031'));
 assert.ok(unfolded.includes('DTEND;VALUE=DATE:20261101'));
 assert.ok(unfolded.includes(event.title));
 for(const line of output.split('\r\n'))assert.ok(Buffer.byteLength(line,'utf8')<=75);
 assert.throws(()=>deadlineICS(COMPETITIONS.find(c=>c.id==='mcm-2027')));
});


test('campus notices separate registration from submissions and preserve the corrected year',()=>{
 const byId=id=>COMPETITIONS.find(c=>c.id===id);
 const ai=byId('suibe-ai-innovation-2026');
 assert.equal(ai.deadline,'2026-11-05');
 assert.equal(competitionStatus(ai,'2026-10-17'),'open');
 assert.ok(ai.team.includes('至少包含 1 名研究生'));
 assert.equal(byId('suibe-business-2027').deadline,'2026-10-15');
 assert.equal(competitionStatus(byId('suibe-business-2027'),'2026-10-17'),'closed');
 assert.equal(byId('suibe-chinese-teaching-4').deadline,'2026-10-16');
 assert.equal(byId('suibe-chinese-teaching-4').deadlineTime,'13:00');
 assert.equal(byId('suibe-constitution-2026').deadline,'2026-10-11');
 assert.equal(byId('suibe-constitution-2026').deadlineTime,'12:00');
 assert.equal(competitionStatus(byId('suibe-constitution-2026'),'2026-10-17'),'closed');
 for(const c of COMPETITIONS){assert.ok(!c.sourceUrl.endsWith('.pdf'));}
 const sourceLinks={
  'suibe-ai-innovation-2026':'BHPqQ-lv4oLskrjKJpuLhw',
  'suibe-finance-case-29':'FcM-3JuyKF139paXWCBjHw',
  'suibe-business-2027':'nFXJu25n8padxK4k3ZmKDg',
  'suibe-chinese-teaching-4':'AygDsSG0K_dsNwQ3z8V3SQ',
  'suibe-constitution-2026':'dXoctTHpowvpbEm6XiPhnw',
  'suibe-wto-moot-7':'zxVm5ruOUQ34VLMiwOAHjw'
 };
 for(const [id,slug] of Object.entries(sourceLinks)){assert.equal(byId(id).sourceUrl,'https://mp.weixin.qq.com/s/'+slug);}
 const wto=byId('suibe-wto-moot-7');
 assert.equal(wto.deadline,'2026-10-23');
 assert.equal(wto.deadlineTime,'18:00');
 assert.ok(wto.team.includes('3–5'));
 assert.equal(competitionStatus(wto,'2026-10-17'),'open');
 assert.ok(wto.notice.includes('截图未显示年份'));
 assert.ok(wto.notice.includes('https://www.wjx.top/vm/hxAe6bU.aspx#'));
 assert.equal(new Set(COMPETITIONS.map(c=>c.id)).size,COMPETITIONS.length);
});
