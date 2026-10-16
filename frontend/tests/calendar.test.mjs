import {test} from 'node:test';
import assert from 'node:assert/strict';
import {addDays,dateNumber,semesterWeek,weekRows,generateCalendar,exportCalendarICS} from '../src/calendar-utils.ts';
const draft={school:'上海对外经贸大学',academicYear:'2026-2027',term:1,start:'2026-09-14',weeks:19,examStart:'2027-01-04',examEnd:'2027-01-15',vacationTitle:'寒假',vacationStart:'2027-01-25',vacationEnd:'2027-02-27',events:[]};
test('19 weeks cross year boundaries and do not assign teaching weeks to holidays',()=>{
 const c=generateCalendar(draft,'test');
 assert.equal(c.end,'2027-01-24');assert.equal(semesterWeek(c,'2026-10-16'),5);
 assert.equal(semesterWeek(c,'2026-09-13'),null);assert.equal(semesterWeek(c,'2027-01-24'),19);assert.equal(semesterWeek(c,'2027-01-25'),null);
 assert.equal(weekRows(c,false).length,19);assert.equal(weekRows(c,true).length,24);assert.equal(weekRows(c,true).at(-1).days.at(-1),'2027-02-28');
 assert.equal(generateCalendar({...draft,start:'2027-03-01',examStart:'2027-06-21',examEnd:'2027-07-02',vacationStart:'2027-07-12',vacationEnd:'2027-09-04'},'spring').end,'2027-07-11');
});
test('generator rejects invalid dates, weekday, ranges, and impossible calendars',()=>{
 for(const patch of [{start:'2026-09-15'},{weeks:0},{weeks:31},{academicYear:'2026-2028'},{examEnd:'2026-12-01'},{vacationStart:'2027-01-24'},{vacationEnd:'2027-01-20'},{events:[{title:'',start:'2026-09-14',end:'2026-09-14'}]}])assert.throws(()=>generateCalendar({...draft,...patch},'bad'));
 assert.throws(()=>dateNumber('2027-02-29'));assert.equal(addDays('2028-02-28',1),'2028-02-29');
});
test('ICS uses exclusive all-day end dates, escaped text and UTF-8 line folding',()=>{
 const c=generateCalendar({...draft,events:[{title:'计划,考试;复习\\备忘\n下一行'+'汉字'.repeat(25),start:'2026-09-15',end:'2026-09-16',kind:'teaching'}]},'export');
 const content=exportCalendarICS(c),unfolded=content.replace(/\r\n /g,'');
 assert.ok(unfolded.includes('DTSTART;VALUE=DATE:20270104\r\nDTEND;VALUE=DATE:20270116'));
 assert.ok(unfolded.includes('DTSTART;VALUE=DATE:20260915\r\nDTEND;VALUE=DATE:20260917'));
 assert.ok(unfolded.includes('计划\\,考试\\;复习\\\\备忘\\n下一行'));
 assert.equal((content.match(/BEGIN:VEVENT/g)||[]).length,c.events.length+19);
 for(const line of content.split('\r\n'))assert.ok(Buffer.byteLength(line,'utf8')<=75);
});
