import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Bell,CalendarDays,ChevronRight,MapPin} from 'lucide-react';
import {api,localDay,readSchedule,parseWeeks} from './api';
import {semesterWeek} from './calendar-utils';
import {OFFICIAL_LINKS} from './links';
const services=[
 {title:'空闲教室',to:'/rooms',art:'📚',color:'mint'},
 {title:'教师检索',to:'/teachers',art:'🔎',color:'blue'},
 {title:'校园地图',to:'/map',art:'🗺️',color:'mint'},
 {title:'课程点评',to:'/courses',art:'💬',color:'coral'},
 {title:'校园食光',to:'/dining',art:'🍜',color:'peach'},
 {title:'赛事广场',to:'/competitions',art:'🏆',color:'peach'},
 {title:'我的课表',to:'/timetable',art:'🗓️',color:'blue'},
 {title:'校历与周次',to:'/calendar',art:'📅',color:'coral'},
];
export default function Home(){
 const [announcements,setAnnouncements]=useState<any[]>([]),[week,setWeek]=useState(0),[semester,setSemester]=useState(''),[error,setError]=useState('');
 useEffect(()=>{Promise.all([api('/announcements'),api('/calendar')]).then(([a,c])=>{setAnnouncements(a);const current=c.find((s:any)=>s.start<=localDay()&&localDay()<=s.end);setWeek(current?semesterWeek(current,localDay())||0:0);setSemester(current?.id||'')}).catch(e=>setError(e.message))},[]);
 const schedule=readSchedule().filter(r=>r.day===((new Date().getDay()+6)%7)+1&&r.semester===semester&&week>0&&parseWeeks(r.weeks).includes(week)).sort((a,b)=>a.start-b.start);
 return <div className="journal-home">
  <div className="journal-greeting"><div><span className="eyebrow">A LITTLE CAMPUS ADVENTURE</span><h1>你好，贸大同学 <span>✦</span></h1><p>把校园日常，过得有点意思。</p></div><Link className="journal-bell" to="/announcements" aria-label="查看校园公告"><Bell size={22}/><i/></Link></div>
  <section className="discovery-hero"><div><span className="hero-label">SUIBE · 校园探索手账</span><h2>今天，<br/>也去发现校园</h2><p>去熟悉的校园，发现新的小惊喜。</p><Link className="primary" to="/map">开启校园探索 <ArrowRight size={17}/></Link></div><span className="discovery-caption">学思楼 · 漫画印象</span></section>
  {error&&<div className="error" role="alert">校园信息加载失败：{error}</div>}
  <div className="section-heading"><h2>校园百宝箱</h2><Link to="/life-guide">生活指南 <ChevronRight size={14}/></Link></div>
  <div className="journal-services">{services.map(s=><Link to={s.to} key={s.to} className={s.color}><span aria-hidden="true">{s.art}</span><strong>{s.title}</strong></Link>)}</div>
  <div className="journal-columns"><section className="panel journal-today"><div className="panel-heading"><h2><CalendarDays size={18}/> 今日安排</h2><Link to="/timetable">查看课表 <ChevronRight size={14}/></Link></div><p className="journal-date">{new Date().toLocaleDateString('zh-CN',{month:'long',day:'numeric',weekday:'long'})} · {week?'第 '+week+' 周':'学期外 / 校历待加载'}</p>{schedule.length?schedule.slice(0,3).map(r=><div className="journal-agenda" key={r.id}><small>第 {r.start}–{r.end} 节</small><strong>{r.name}</strong><span><MapPin size={13}/>{r.room||'教室待设置'}{r.teacher?' · '+r.teacher:''}</span></div>):<div className="journal-agenda"><small>给今天留一点自由</small><strong>还没有今日课程安排</strong><span>添加课表，把校园节奏握在手里。</span><Link to="/timetable">去添加课程 <ArrowRight size={14}/></Link></div>}</section>
  <section className="panel journal-notices"><div className="panel-heading"><h2><Bell size={18}/> 校园新鲜事</h2><Link to="/announcements">全部 <ChevronRight size={14}/></Link></div>{announcements.slice(0,3).map(a=><Link className="announcement-row" key={a.id} to={'/announcements?id='+a.id}><div><h3>{a.title}</h3><p>{a.department} · {a.date}</p></div><ChevronRight size={14}/></Link>)}{!announcements.length&&<p>校园公告加载后会在这里显示。</p>}</section></div>
  <div className="journal-promos"><Link to="/dining"><div><h3>一口校园，<br/>收进邮筒</h3><p>用美食记录生活 <ArrowRight size={14}/></p></div><span aria-hidden="true">🍜</span></Link><Link to="/competitions"><div><h3>下一场挑战，<br/>等你出发</h3><p>让热爱发光 <ArrowRight size={14}/></p></div><span aria-hidden="true">🏆</span></Link></div>
  <section className="journal-links"><Link to="/assistant">✦ AI 校园助手 <ArrowRight size={15}/></Link>{OFFICIAL_LINKS.map(l=><a key={l.url} href={l.url} target="_blank" rel="noreferrer">{l.name} ↗</a>)}</section><p className="journal-disclaimer">学生创新项目 · 教师、教室占用及课程点评目录含示例数据；服务指南与赛事信息注明来源。</p>
 </div>
}
