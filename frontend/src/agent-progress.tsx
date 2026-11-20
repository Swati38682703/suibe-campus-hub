import {useEffect,useState} from 'react';
import type {AgentProgress} from './agent-stream';
import './agent-progress.css';

export default function AgentProgressView({events,startedAt,lastSeen,onStop}:{events:AgentProgress[];startedAt:number;lastSeen:number;onStop:()=>void}){
 const [now,setNow]=useState(Date.now());
 useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[]);
 const steps=events.filter(e=>e.type==='tool_start'||e.type==='tool_end');
 const current=events.filter(e=>e.type!=='heartbeat').at(-1);
 const label=current?.type==='tool_start'?current.label+'…':current?.type==='tool_end'?(current.label+(current.status==='error'?'未完成':'已返回')):current?.label||'正在连接校园助手…';
 const rows:{label:string;state:'running'|'done'|'error';tool?:string}[]=[];
 for(const step of steps){
  if(step.type==='tool_start')rows.push({label:step.label||'查询校园工具',state:'running',tool:step.tool});
  else{const row=[...rows].reverse().find(r=>r.tool===step.tool&&r.state==='running');if(row)row.state=step.status==='error'?'error':'done'}
 }
 const silent=now-lastSeen>15000;
 return <div className="agent-progress" role="status" aria-label="贝贝执行进度">
  <div className="agent-progress-heading"><span className="status-dot"/><strong>{label}</strong></div>
  <div className="agent-progress-meta"><span aria-live="off">已等待 {Math.max(0,Math.floor((now-startedAt)/1000))} 秒</span><button type="button" className="text-button" onClick={onStop}>停止等待</button></div>
  {rows.length>0&&<ol>{rows.map((row,i)=><li key={i} data-state={row.state}><span aria-hidden="true">{row.state==='done'?'✓':row.state==='error'?'!':'◌'}</span>{row.label}<small>{row.state==='done'?'已返回':row.state==='error'?'未完成':'进行中'}</small></li>)}</ol>}
  {silent?<p>暂未收到新的服务信号，正在等待连接恢复。</p>:now-startedAt>20000&&<p>仍在等待服务响应，可继续等待或停止本次等待。</p>}
 </div>;
}
