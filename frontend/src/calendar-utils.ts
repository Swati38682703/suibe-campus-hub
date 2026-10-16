export interface CalendarEvent {id:string;title:string;start:string;end:string;kind:string;note?:string}
export interface AcademicCalendar {id:string;school:string;academicYear:string;term:number;title:string;start:string;end:string;weeks:number;source:string;source_image?:string;custom?:boolean;vacation?:{title:string;start:string;end:string};events:CalendarEvent[]}
const DAY=86400000;
export function dateNumber(value:string):number {
 const date=new Date(value+'T00:00:00Z');
 if(!/^\d{4}-\d{2}-\d{2}$/.test(value)||!Number.isFinite(date.getTime())||date.toISOString().slice(0,10)!==value)throw new Error('日期格式无效');
 return date.getTime();
}
export function addDays(value:string,days:number):string {return new Date(dateNumber(value)+days*DAY).toISOString().slice(0,10)}
export function semesterWeek(calendar:Pick<AcademicCalendar,'start'|'end'>,day:string):number|null {return day<calendar.start||day>calendar.end?null:Math.floor((dateNumber(day)-dateNumber(calendar.start))/(7*DAY))+1}
export function weekRows(calendar:AcademicCalendar,includeVacation=true) {
 const last=includeVacation&&calendar.vacation?calendar.vacation.end:calendar.end;
 const count=Math.ceil((dateNumber(last)-dateNumber(calendar.start)+DAY)/(7*DAY));
 return Array.from({length:count},(_,i)=>({week:i<calendar.weeks?i+1:null,days:Array.from({length:7},(_,d)=>addDays(calendar.start,i*7+d))}));
}
export function dayEvents(calendar:AcademicCalendar,day:string){return calendar.events.filter(e=>e.start<=day&&day<=e.end)}
export interface CalendarDraft {school:string;academicYear:string;term:number;start:string;weeks:number;examStart:string;examEnd:string;vacationTitle:string;vacationStart:string;vacationEnd:string;events:CalendarEvent[]}
export function generateCalendar(draft:CalendarDraft,id='custom-'+crypto.randomUUID()):AcademicCalendar {
 if(!draft.school.trim()||!/^\d{4}-\d{4}$/.test(draft.academicYear)||Number(draft.academicYear.slice(5))!==Number(draft.academicYear.slice(0,4))+1)throw new Error('请填写学校和连续两年的学年，例如 2026-2027');
 if(![1,2].includes(draft.term)||!Number.isInteger(draft.weeks)||draft.weeks<1||draft.weeks>30)throw new Error('学期须为 1 或 2，周数须为 1–30');
 if(new Date(dateNumber(draft.start)).getUTCDay()!==1)throw new Error('请选择开学首周的周一，周次从该日计算');
 const end=addDays(draft.start,draft.weeks*7-1),events:CalendarEvent[]=[{id:'classes',title:'开学上课',start:draft.start,end:draft.start,kind:'teaching'}];
 if(draft.examStart||draft.examEnd){dateNumber(draft.examStart);dateNumber(draft.examEnd);if(draft.examStart>draft.examEnd||draft.examStart<draft.start||draft.examEnd>end)throw new Error('考试日期应在学期内，结束日期不能早于开始日期');events.push({id:'finals',title:'期末考试',start:draft.examStart,end:draft.examEnd,kind:'exam'})}
 let vacation:AcademicCalendar['vacation'];
 if(draft.vacationStart||draft.vacationEnd){dateNumber(draft.vacationStart);dateNumber(draft.vacationEnd);if(draft.vacationStart<=end||draft.vacationStart>draft.vacationEnd||dateNumber(draft.vacationEnd)-dateNumber(end)>180*DAY)throw new Error('假期应在学期结束之后，结束不能早于开始，且不超过学期结束后 180 天');vacation={title:draft.vacationTitle.trim()||'假期',start:draft.vacationStart,end:draft.vacationEnd};events.push({id:'vacation',...vacation,kind:'vacation'})}
 for(const [index,event] of draft.events.entries()){dateNumber(event.start);dateNumber(event.end);if(!event.title.trim()||event.title.length>80||event.start>event.end)throw new Error('请检查自定义事项的标题和日期范围');if(event.start<addDays(draft.start,-30)||event.end>(vacation?.end||end))throw new Error('自定义事项须在开学前 30 天至校历结束之间');events.push({...event,id:'extra-'+index,title:event.title.trim()})}
 return {id,school:draft.school.trim(),academicYear:draft.academicYear,term:draft.term,title:`${draft.academicYear} 学年第${draft.term===1?'一':'二'}学期`,start:draft.start,end,weeks:draft.weeks,events,vacation,source:'本机自定义生成，非学校发布',custom:true};
}
function icsText(value:string){return value.replace(/\\/g,'\\\\').replace(/\r?\n/g,'\\n').replace(/;/g,'\\;').replace(/,/g,'\\,')}
export function exportCalendarICS(calendar:AcademicCalendar):string {
 const records=[...calendar.events,...weekRows(calendar,false).map(r=>({id:'week-'+r.week,title:`第 ${r.week} 周`,start:r.days[0],end:r.days[6],kind:'week',note:calendar.title}))];
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//SUIBE Campus Hub//Academic Calendar//ZH','CALSCALE:GREGORIAN','X-WR-CALNAME:'+icsText(calendar.school+' '+calendar.title),'X-WR-TIMEZONE:Asia/Shanghai'];
 for(const event of records){lines.push('BEGIN:VEVENT','UID:'+icsText(calendar.id+'-'+event.id)+'@campus-hub.local','DTSTAMP:'+new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}Z/,'Z'),'DTSTART;VALUE=DATE:'+event.start.replaceAll('-',''),'DTEND;VALUE=DATE:'+addDays(event.end,1).replaceAll('-',''),'SUMMARY:'+icsText(event.title),'DESCRIPTION:'+icsText([event.note,calendar.source,'节日日期不代表完整放假调休安排'].filter(Boolean).join('\n')),'END:VEVENT')}
 lines.push('END:VCALENDAR');
 // Fold by UTF-8 bytes so long Chinese summaries remain valid iCalendar content lines.
 return lines.map(line=>{const parts:string[]=[];let part='',length=0;for(const char of line){const bytes=new TextEncoder().encode(char).length;if(length+bytes>75){parts.push(part);part=' ';length=1}part+=char;length+=bytes}parts.push(part);return parts.join('\r\n')}).join('\r\n')+'\r\n';
}
