export interface Competition {
 id:string; title:string; scope:'campus'|'major'; field:string; level:string; organizer:string;
 summary:string; audience:string; team:string; schedule:string; published?:string;
 registrationStart?:string; deadline?:string; endedOn?:string; source:string; sourceUrl:string;
 website?:string; checked:string; notice:string;
}
export const COMPETITIONS: Competition[]=[
 {id:'market-17',title:'“正大杯”第十七届全国大学生市场调查与分析大赛',scope:'major',field:'经管商科',level:'全国赛事',organizer:'中国商业统计学会',summary:'从真实问题出发，完成市场调研、数据分析与报告展示。',audience:'本科生；研究生及留学生组规则另见原文',team:'实践赛每队 3–5 人，同校组队',schedule:'本科组知识赛：2026-11-01 至 11-20',published:'2026-10-12',deadline:'2026-10-31',source:'上海外国语大学教务处转发全国赛事通知',sourceUrl:'https://newoaa.shisu.edu.cn/3c/b9/c6353a212153/page.htm',website:'http://www.china-cssc.org/list-60-1.html',checked:'2026-10-16',notice:'展示的是全国本科组截止日期。本校是否组织参赛、校内提前截止时间及院校代码须向本校确认；请勿使用其他学校代码。研究生及留学生组原文截止为 11 月 15 日。'},
 {id:'mcm-2027',title:'2027 MCM / ICM 美国大学生数学建模竞赛',scope:'major',field:'数学建模',level:'国际赛事',organizer:'COMAP',summary:'围绕开放问题开展数学建模，兼顾研究、分析、协作与报告表达。',audience:'大学本科生等，具体资格见主办方规则',team:'每队最多 3 人',schedule:'2027-01-28 至 02-01（主办方公布日期）',source:'COMAP 主办方赛事页面',sourceUrl:'https://comap.org/contests/mcm-icm',website:'https://comap.org/contests/mcm-icm',checked:'2026-10-16',notice:'已核实比赛日期，尚未录入报名起止时间；请查看当届报名规则、费用和时区，本卡片不表示正在报名。'},
 {id:'ai-literacy-2026',title:'2026 年大学生“AI+信息素养”大赛',scope:'major',field:'人工智能',level:'跨地区高校赛事',organizer:'大学生信息素养大赛组织委员会',summary:'面向人工智能时代的信息获取、检索、评价与应用能力。',audience:'本科生、研究生、高职高专等赛道',team:'学校选拔赛后，按赛道规则组队晋级',registrationStart:'2026-07-03',deadline:'2026-09-17',schedule:'省赛：10-17 至 11-02；联赛拟于 11-26 至 11-27',source:'大赛官方平台',sourceUrl:'https://csc.xxsuyang.com/intro',website:'https://csc.xxsuyang.com/',checked:'2026-10-16',notice:'个人初次报名已截止；省赛团队报名截止为 10 月 11 日。后续赛程面向符合晋级条件的选手，不代表可重新报名。'},
 {id:'suibe-ai-2026',title:'大学生“AI+信息素养”大赛 · 校内选拔关注',scope:'campus',field:'人工智能',level:'校内选拔',organizer:'校内通知入口：学校图书馆',summary:'图书馆已发布当届大赛报名通知，可从校内原文了解本校组织安排。',audience:'本校参赛资格及赛道以图书馆通知为准',team:'以学校通知及官方赛制为准',deadline:'2026-09-17',schedule:'官方统一校选赛时段：2026-09-19 至 09-21',source:'上海对外经贸大学图书馆；日期参考赛事官方平台',sourceUrl:'https://lib.suibe.edu.cn/_redirect?siteId=4&columnId=19&articleId=14835',website:'https://csc.xxsuyang.com/',checked:'2026-10-16',notice:'学校官网可检索到本届通知；本卡采用主办方统一日期，校内具体安排仍须阅读图书馆原文。当前初次报名已截止。'},
 {id:'suibe-ecommerce-16',title:'第十六届全国大学生电子商务“三创赛” · 校赛回顾',scope:'campus',field:'创新创业',level:'校内选拔',organizer:'上海对外经贸大学校赛',summary:'校赛涉及电商创新与实践项目，可了解选拔形式并准备后续届次。',audience:'往届参赛情况参考，非新一届招募',team:'新一届组队规则待正式通知',endedOn:'2026-04-25',schedule:'本届校赛已于 2026-04-25 举行',published:'2026-04-29',source:'上海对外经贸大学教务处',sourceUrl:'https://jwc.suibe.edu.cn/2026/0429/c18756a194789/page.htm',checked:'2026-10-16',notice:'这是本年度校赛报道，不是近期报名通知；新一届报名时间尚未录入，不据往年时间推算。'},
];
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
