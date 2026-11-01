import {CSSProperties, useEffect, useRef, useState} from 'react';
import {Link, useLocation} from 'react-router-dom';
import {ArrowUpRight, X} from 'lucide-react';
import {Assistant} from './pages';
import BeibeiFace from './beibei-face';
import {beibeiImage, beibeiThemeForPath, beibeiThemes} from './beibei-themes';
import './beibei.css';

export default function BeibeiAssistant(){
 const [open,setOpen]=useState(false),[started,setStarted]=useState(false);
 const [activity,setActivity]=useState<'idle'|'thinking'|'happy'|'error'>('idle'),[reaction,setReaction]=useState(0);
 useEffect(()=>{if(activity!=='happy')return;const timer=window.setTimeout(()=>setActivity('idle'),2600);return()=>clearTimeout(timer)},[activity]);
 const launcher=useRef<HTMLButtonElement>(null),panel=useRef<HTMLElement>(null);
 const location=useLocation();
 const themeId=beibeiThemeForPath(location.pathname),theme=beibeiThemes[themeId];
 const [image,setImage]=useState(beibeiImage(themeId));
 useEffect(()=>{
  let active=true;
  const next=new Image();
  next.onload=()=>{if(active)setImage(next.src)};
  next.onerror=()=>{if(active)setImage(beibeiImage('campus'))};
  next.src=beibeiImage(themeId);
  return()=>{active=false};
 },[themeId]);
 const close=()=>{setOpen(false);launcher.current?.focus()};
 useEffect(()=>{setOpen(false)},[location.pathname]);
 useEffect(()=>{
  if(!open)return;
  panel.current?.querySelector<HTMLTextAreaElement>('textarea')?.focus({preventScroll:true});
  const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'){setOpen(false);launcher.current?.focus()}};
  document.addEventListener('keydown',escape);
  return()=>document.removeEventListener('keydown',escape);
 },[open]);
 return <div className={'beibei-widget'+(open?' chat-open':'')} data-theme={themeId} data-motion={theme.motion} data-activity={activity} style={{'--beibei-accent':theme.accent} as CSSProperties}>
  {started&&<section ref={panel} id="beibei-dialog" className="beibei-dialog" role="dialog" aria-labelledby="beibei-title" hidden={!open}>
   <header className="beibei-header"><img src={image} alt=""/><div><h2 id="beibei-title">贝贝 · {theme.title}</h2><p>{theme.hint}</p></div><Link to="/assistant" aria-label="打开完整助手页面" title="打开完整助手页面"><ArrowUpRight size={19}/></Link><button type="button" aria-label="收起贝贝对话框" onClick={close}><X size={20}/></button></header>
   <div className="beibei-chat"><Assistant compact onActivity={setActivity}/></div>
  </section>}
  <button ref={launcher} type="button" className={'beibei-launcher '+(open?'is-open':'')} aria-label={open?'收起贝贝对话框':'打开贝贝校园助手'} aria-expanded={open} aria-controls={started?'beibei-dialog':undefined} onClick={()=>{setReaction(n=>n+1);if(open)close();else{setStarted(true);setOpen(true)}}}>
   <span className="beibei-greeting" role="status">{activity==='thinking'?'贝贝正在认真查找…':activity==='happy'?'找到啦，一起看看！':activity==='error'?'暂时没连上，陪你再试一次':theme.greeting}</span><span key={themeId} className="beibei-entrance"><span className="beibei-ground" aria-hidden="true"/><span className="beibei-character"><BeibeiFace themeId={themeId} image={image} activity={activity} poke={reaction}/><span className="beibei-emote" aria-hidden="true">{activity==='thinking'?'···':activity==='happy'?'✓':activity==='error'?'?':'♡'}</span><span className="beibei-confetti" aria-hidden="true"><i>✦</i><i>✧</i><i>✦</i></span><span className="beibei-sparkle" aria-hidden="true">✦</span></span></span><span className="beibei-name">{activity==='thinking'?'认真查找中…':activity==='happy'?'找到答案啦':open?'收起对话':theme.title}</span>
  </button>
 </div>;
}
