import {useEffect,useState} from 'react';
import {api} from './api';
import type {RoomSnapshot} from './room-filter';

type Snapshot={date:string;rows:RoomSnapshot[];updatedAt:string|null;ageSeconds:number|null;stale:boolean;refreshing:boolean;error:string;state:string};
export function useRoomSnapshot(day:string,refresh:number){
 const [state,setState]=useState<{day:string;snapshot:Snapshot|null;error:string;received:number}>({day,snapshot:null,error:'',received:0});
 const [clock,setClock]=useState(0);
 useEffect(()=>{const timer=setInterval(()=>setClock(Date.now()),1000);return()=>clearInterval(timer)},[]);
 useEffect(()=>{
  let live=true,first=true,timer:ReturnType<typeof setTimeout>|undefined;
  const controller=new AbortController();
  const load=async()=>{
   let delay=15000;
   try{
    const value=await api<Snapshot>('/rooms/snapshot?'+new URLSearchParams({date:day,refresh:String(first&&refresh>0)}),{signal:controller.signal});
    first=false;
    if(live)setState({day,snapshot:value,error:'',received:Date.now()});
    delay=value.refreshing?2000:value.state==='warming'?10000:15000;
   }catch(e){if(live)setState(previous=>previous.day===day&&previous.snapshot?.rows.length?{...previous,error:'读取更新失败，当前仅为上次快照，请核对学校原文。'}:{day,snapshot:null,error:e instanceof Error?e.message:'教室查询失败',received:0})}
   if(live)timer=setTimeout(load,delay);
  };
  void load();
  return()=>{live=false;controller.abort();if(timer)clearTimeout(timer)};
 },[day,refresh]);
 const current=state.day===day?state:{day,snapshot:null,error:'',received:0};
 const metadata=current.snapshot;
 const age=metadata?.ageSeconds==null?null:metadata.ageSeconds+Math.max(0,Math.floor(((clock||Date.now())-current.received)/1000));
 const stale=!!current.error||!!metadata?.error||!!metadata?.stale||(age!==null&&age>=60);
 return {data:metadata&&metadata.state!=='warming'?metadata.rows:null,error:metadata?.rows.length?'':current.error,
  metadata,stale,warning:current.error||metadata?.error||'',age};
}
