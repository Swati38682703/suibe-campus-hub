import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserRouter, Link, NavLink, Route, Routes, useLocation, useNavigate} from 'react-router-dom';
import {ArrowLeft, ArrowRight, Bell, BookOpen, CalendarDays, Check, ChevronRight, Compass, GraduationCap, LayoutDashboard, MessageCircle, Search, ShieldCheck, Sparkles, Users, Menu, X, Trophy, Bot} from 'lucide-react';
import {api} from './api';
import {Assistant, Courses, RoomDetail, Rooms, Teachers, Timetable, Admin as ServerAdmin, Announcements, Profile, LifeGuide} from './pages';
import {NoticeContext,Empty,PageTitle} from './ui';
import CalendarPage from './calendar';
import DiningPage from './dining';
import CompetitionsPage from './competitions';
import Home from './home';
import AdminDemo from './admin-demo';
import './style.css';
import './blue-theme.css';
import './mobile.css';
import './journal.css';
import './campus-icons.css';
import './campus-updates.css';
const MapPage=React.lazy(()=>import('./map'));

const navigation=[{href:'/',label:'校园概览',icon:LayoutDashboard},{href:'/assistant',label:'AI 校园助手',icon:Bot},{href:'/rooms',label:'空闲教室',icon:BookOpen},{href:'/teachers',label:'教师检索',icon:Users},{href:'/map',label:'校园平面地图',icon:Compass},{href:'/courses',label:'课程点评',icon:GraduationCap},{href:'/competitions',label:'赛事广场',icon:Trophy},{href:'/dining',label:'校园食光',icon:Compass},{href:'/life-guide',label:'生活指南',icon:Compass},{href:'/timetable',label:'我的课表',icon:CalendarDays},{href:'/calendar',label:'校历与周次',icon:CalendarDays}];
function Shell(){
 const [notice,setNotice]=useState(''),[mobile,setMobile]=useState(false),[query,setQuery]=useState('');
 const location=useLocation(),navigate=useNavigate();
 const isAdminDemo=location.pathname==='/admin';
 const backTarget=location.pathname.startsWith('/rooms/')?'/rooms'+(location.search||''):location.pathname.startsWith('/courses/')?'/courses':location.pathname==='/admin/server'?'/admin':'/';
 const goBack=()=>{if(Number(window.history.state?.idx)>0)navigate(-1);else navigate(backTarget,{replace:true})};
 useEffect(()=>{setMobile(false);window.scrollTo(0,0)},[location.pathname]);
 useEffect(()=>{if(notice){const timer=setTimeout(()=>setNotice(''),5000);return()=>clearTimeout(timer)}},[notice]);
 return <NoticeContext.Provider value={setNotice}><div className="app-shell">
  <aside className={'sidebar '+(mobile?'open':'')}><Link className="brand" to="/"><span className="school-seal" role="img" aria-label="上海对外经贸大学校徽"/><span>SUIBE<span className="brand-sub">CAMPUS HUB</span><span className="brand-school-name">上海对外经贸大学</span></span></Link>
   <div className="nav-label">校园服务 / CAMPUS</div><nav>{navigation.map(n=><NavLink key={n.href} to={n.href} end={n.href==='/'}><n.icon size={19}/>{n.label}{n.href==='/assistant'&&<span className="tiny-tag">AI</span>}</NavLink>)}</nav>
   <div className="sidebar-bottom"><div className="campus-indicator"><span className="status-dot"/>松江校区<span>公开浏览</span></div><Link to="/announcements"><Bell size={17}/> 校园公告<ChevronRight size={15}/></Link><Link to="/profile"><MessageCircle size={17}/> 我的收藏与反馈<ChevronRight size={15}/></Link><div className="sidebar-note">为每一天的校园生活<br/>少一点寻找，多一点从容。</div><span className="small">学生创新项目 · 演示版 v0.1</span></div>
  </aside>{mobile&&<button className="scrim" aria-label="关闭导航" onClick={()=>setMobile(false)}/>}
  <div className="main-shell"><header className="topbar"><button className="mobile-menu icon-button" aria-label="打开导航" onClick={()=>setMobile(!mobile)}>{mobile?<X/>:<Menu/>}</button><Link className="mobile-brand" to="/"><span className="school-seal"/><strong>贸大校园助手</strong></Link><div className="breadcrumb">校园服务 <ChevronRight size={13}/><strong>{(isAdminDemo?'管理员工作台':navigation.find(n=>n.href===location.pathname)?.label)||'服务详情'}</strong></div><form className="global-search" onSubmit={e=>{e.preventDefault();navigate('/search?q='+encodeURIComponent(query))}}><Search size={16}/><input aria-label="全站搜索" placeholder="搜索教师、课程、教室…" value={query} onChange={e=>setQuery(e.target.value)}/><kbd>↵</kbd></form><div className="demo-role-switch" aria-label="演示角色切换"><Link className={!isAdminDemo?'active':''} to="/"><Users size={14}/>用户视图</Link><Link className={isAdminDemo?'active':''} to="/admin"><ShieldCheck size={14}/>管理员视图</Link></div><Link className="avatar" aria-label="个人中心" to="/profile">贸</Link></header>
   <main>{location.pathname!=='/'&&<nav className="page-back-nav" aria-label="页面返回导航"><button type="button" onClick={goBack}><ArrowLeft size={17}/>返回上一页</button><Link to="/">返回首页</Link></nav>}<div className="demo-mode-note"><span>学校展示模式 · {isAdminDemo?'管理员视图':'用户视图'}</span><small>角色切换无需登录 · 真实点评审核需管理凭证</small></div><React.Suspense fallback={<Empty>正在加载校园地图…</Empty>}><Routes><Route path="/" element={<Home/>}/><Route path="/assistant" element={<Assistant/>}/><Route path="/rooms" element={<Rooms/>}/><Route path="/rooms/:id" element={<RoomDetail/>}/><Route path="/teachers" element={<Teachers/>}/><Route path="/map" element={<MapPage/>}/><Route path="/courses" element={<Courses/>}/><Route path="/courses/:id" element={<Courses/>}/><Route path="/competitions" element={<CompetitionsPage/>}/><Route path="/dining" element={<DiningPage/>}/><Route path="/life-guide" element={<LifeGuide/>}/><Route path="/timetable" element={<Timetable/>}/><Route path="/announcements" element={<Announcements/>}/><Route path="/calendar" element={<CalendarPage/>}/><Route path="/profile" element={<Profile/>}/><Route path="/admin" element={<AdminDemo/>}/><Route path="/admin/server" element={<ServerAdmin/>}/><Route path="/search" element={<SearchPage/>}/><Route path="*" element={<Empty>页面不存在，<Link to="/">返回首页</Link></Empty>}/></Routes></React.Suspense></main>
   <nav className="mobile-bottom-nav" aria-label="手机常用服务">{[{to:'/',label:'首页',icon:LayoutDashboard},{to:'/assistant',label:'助手',icon:Bot},{to:'/dining',label:'食光',icon:Compass},{to:'/timetable',label:'课表',icon:CalendarDays},{to:'/profile',label:'我的',icon:Users}].map(n=><NavLink key={n.to} to={n.to} end={n.to==='/'}><n.icon size={21}/><span>{n.label}</span></NavLink>)}</nav>
   <footer><span>© 2026 SUIBE Campus Hub · 校园智慧服务一体化平台</span><span>服务指南有出处 · 学生创新项目 <Link to="/admin">管理员演示入口</Link></span></footer>
  </div>{notice&&<div className="toast" role="status"><Check size={18}/>{notice}</div>}
 </div></NoticeContext.Provider>
}

function SearchPage(){const {search}=useLocation();const query=new URLSearchParams(search).get('q')||'';const [rows,setRows]=useState<any[]|null>(null),[error,setError]=useState('');useEffect(()=>{let live=true;setRows(null);setError('');api('/search?q='+encodeURIComponent(query)).then(data=>{if(live)setRows(data)}).catch(e=>{if(live)setError(e.message)});return()=>{live=false}},[query]);const urls:Record<string,string>={teachers:'/teachers',courses:'/courses/',rooms:'/rooms/',announcements:'/announcements?id=',buildings:'/map?building=',knowledge:'/assistant'};return <><PageTitle eyebrow="SEARCH" title={'搜索：'+query} description="跨教室、教师、课程、公告与校园知识查询"/>{error&&<div className="error">{error}</div>}{rows?.length?<div className="result-list">{rows.map(r=><Link className="panel search-result" key={r.kind+r.id} to={urls[r.kind]+(['teachers','knowledge'].includes(r.kind)?'':r.id)}><span className="badge">{({teachers:'教师',courses:'课程',rooms:'教室',announcements:'公告',buildings:'校园建筑',knowledge:'办事指南'} as Record<string,string>)[r.kind]||'校园信息'}</span><h3>{r.name||r.title}</h3><p>{r.department||r.text||r.description||r.source}</p><ArrowRight size={16}/></Link>)}</div>:error?null:<Empty>{rows===null?'正在搜索校园信息…':'没有找到结果，试试“图书馆”“A101”或“数据分析”。'}</Empty>}</>}

createRoot(document.getElementById('root')!).render(<BrowserRouter><Shell/></BrowserRouter>);
