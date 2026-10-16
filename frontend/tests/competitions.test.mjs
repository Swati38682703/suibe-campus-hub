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
