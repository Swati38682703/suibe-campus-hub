import {useEffect,useRef,useState} from 'react';
import {beibeiExpressions,beibeiGazeFrame,beibeiSpritePosition,BeibeiExpression} from './beibei-gaze';
import {BeibeiThemeId} from './beibei-themes';

type Activity='idle'|'thinking'|'happy'|'error';
export default function BeibeiFace({themeId,image,activity,poke}:{themeId:BeibeiThemeId;image:string;activity:Activity;poke:number}){
 const root=useRef<HTMLSpanElement>(null),previous=useRef(4),lastPoke=useRef({time:0,count:0});
 const [ready,setReady]=useState(false),[direction,setDirection]=useState(4),[expression,setExpression]=useState<BeibeiExpression|null>(null),[sleeping,setSleeping]=useState(false);
 const atlas=`/assets/beibei/sprites/${themeId}-expressions-v2.webp`;
 useEffect(()=>{let active=true;setReady(false);const img=new Image();img.onload=()=>{if(active)setReady(true)};img.src=atlas;return()=>{active=false}},[atlas]);
 useEffect(()=>{
  const fine=window.matchMedia('(hover: hover) and (pointer: fine)'),reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  let frame=0,idle=0,point:{x:number;y:number}|null=null;
  const reset=()=>{previous.current=4;setDirection(4);setSleeping(false)};
  const scheduleSleep=()=>{clearTimeout(idle);if(fine.matches&&!reduced.matches)idle=window.setTimeout(()=>{setSleeping(true);previous.current=4;setDirection(4)},22000)};
  const aim=()=>{frame=0;if(!point||!root.current)return;const rect=root.current.getBoundingClientRect();const next=beibeiGazeFrame(point.x-rect.left-rect.width/2,point.y-rect.top-rect.height*.37,previous.current);previous.current=next;setDirection(next)};
  const schedule=()=>{if(!frame)frame=requestAnimationFrame(aim)};
  const move=(event:PointerEvent)=>{if(event.pointerType==='touch'||!fine.matches||reduced.matches)return;point={x:event.clientX,y:event.clientY};setSleeping(false);scheduleSleep();schedule()};
  const wake=()=>{setSleeping(false);scheduleSleep()};
  const leave=(event:PointerEvent)=>{if(event.relatedTarget===null){point=null;reset()}};
  const media=()=>{if(!fine.matches||reduced.matches){clearTimeout(idle);point=null;reset()}else scheduleSleep()};
  window.addEventListener('keydown',wake);window.addEventListener('pointermove',move,{passive:true});window.addEventListener('pointerout',leave);window.addEventListener('blur',reset);window.addEventListener('scroll',schedule,{passive:true});window.addEventListener('resize',schedule);
  fine.addEventListener('change',media);reduced.addEventListener('change',media);scheduleSleep();
  return()=>{window.removeEventListener('keydown',wake);cancelAnimationFrame(frame);clearTimeout(idle);window.removeEventListener('pointermove',move);window.removeEventListener('pointerout',leave);window.removeEventListener('blur',reset);window.removeEventListener('scroll',schedule);window.removeEventListener('resize',schedule);fine.removeEventListener('change',media);reduced.removeEventListener('change',media)};
 },[]);
 useEffect(()=>{
  if(activity!=='idle'){setExpression(null);setSleeping(false);return;}
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');let blink=0,release=0;
  const plan=()=>{blink=window.setTimeout(()=>{if(!reduced.matches){setExpression('blink');release=window.setTimeout(()=>setExpression(null),150)}plan()},4500+Math.random()*2200)};
  plan();return()=>{clearTimeout(blink);clearTimeout(release)};
 },[activity,poke]);
 useEffect(()=>{
  if(!poke)return;
  const now=Date.now(),last=lastPoke.current;last.count=now-last.time<1600?last.count+1:1;last.time=now;
  const dizzy=last.count>=4;if(dizzy)last.count=0;
  setSleeping(false);setExpression(dizzy?'dizzy':'blink');
  const payoff=dizzy?0:window.setTimeout(()=>setExpression(poke%2?'wink':'happy'),130);
  const release=window.setTimeout(()=>setExpression(null),dizzy?1200:900);
  return()=>{clearTimeout(payoff);clearTimeout(release)};
 },[poke]);
 const face=activity==='thinking'?'thinking':activity==='happy'?'happy':activity==='error'?'surprised':expression||(sleeping?'sleepy':null);
 const cell=face?beibeiExpressions[face]:direction;
 return <span ref={root} className="beibei-portrait" data-direction={direction} data-expression={face||'neutral'} data-sprite-ready={ready}>
  <span key={poke} className={poke?'beibei-sprite-bounce':'beibei-sprite-still'}>
   <img src={image} alt="" draggable={false} style={{visibility:ready?'hidden':'visible'}}/>
   {ready&&<span className="beibei-sprite" aria-hidden="true" data-frame={cell} style={{backgroundImage:`url(${atlas})`,backgroundPosition:beibeiSpritePosition(cell)}}/>}
  </span>
 </span>;
}
