import competitionRows from '../../data/competitions.json' with {type:'json'};
export interface Competition {
 id:string; title:string; scope:'campus'|'major'; field:string; level:string; organizer:string;
 summary:string; audience:string; team:string; schedule:string; published?:string;
 registrationStart?:string; deadline?:string; endedOn?:string; source:string; sourceUrl:string;
 website?:string; checked:string; notice:string; deadlineTime?:string; sourceFormat?:'pdf'|'wechat'|'website';
}
export const COMPETITIONS=competitionRows as Competition[];
export type CompetitionStatus='open'|'upcoming'|'closed'|'unknown';
export function shanghaiDay(now=new Date()):string {
 const p=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
 return ['year','month','day'].map(k=>p.find(v=>v.type===k)!.value).join('-');
}
export function daysBetween(a:string,b:string):number {return Math.round((Date.parse(b+'T00:00:00+08:00')-Date.parse(a+'T00:00:00+08:00'))/86400000)}
export function competitionStatus(c:Competition,today=shanghaiDay()):CompetitionStatus {
 if((c.endedOn&&c.endedOn<today)||(c.deadline&&c.deadline<today))return 'closed';
 if(!c.deadline||daysBetween(c.checked,today)>7)return 'unknown';
 if(c.registrationStart&&c.registrationStart>today)return 'upcoming';
 return 'open';
}
export const STATUS_LABELS:Record<CompetitionStatus,string>={open:'报名期内',upcoming:'即将开放',closed:'报名已截止 / 已结束',unknown:'报名待核实'};
export function deadlineICS(c:Competition):string {
 if(!c.deadline)throw new Error('尚未确认报名截止日期');
 const escape=(s:string)=>s.replace(/\\/g,'\\\\').replace(/\n/g,'\\n').replace(/,/g,'\\,').replace(/;/g,'\\;');
 const next=new Date(c.deadline+'T00:00:00Z');next.setUTCDate(next.getUTCDate()+1);
 const lines=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//SUIBE Campus Hub//Competitions//ZH','BEGIN:VEVENT','UID:'+c.id+'-deadline@suibe-campus-hub.local','DTSTAMP:'+new Date().toISOString().replace(/[-:]/g,'').replace(/\.\d{3}/,''),'DTSTART;VALUE=DATE:'+c.deadline.replace(/-/g,''),'DTEND;VALUE=DATE:'+next.toISOString().slice(0,10).replace(/-/g,''),'SUMMARY:'+escape('报名截止 · '+c.title),'DESCRIPTION:'+escape(c.notice+'\n来源：'+c.sourceUrl),'END:VEVENT','END:VCALENDAR'];
 // Fold UTF-8 lines without splitting multibyte characters (RFC 5545).
 return lines.map(line=>{let result='',part='';for(const ch of line){if(new TextEncoder().encode(part+ch).length>75){result+=part+'\r\n';part=' '}part+=ch}return result+part}).join('\r\n')+'\r\n';
}
