import {useEffect,useState} from 'react';
import {api} from './api';
import type {RoomSnapshot} from './room-filter';

export function useRoomSnapshot(day:string,refresh:number){
 const [state,setState]=useState<{day:string;data:RoomSnapshot[]|null;error:string}>({day,data:null,error:''});
 useEffect(()=>{
  let live=true,timer:ReturnType<typeof setTimeout>|undefined;
  const controller=new AbortController();
  const load=async()=>{
   setState({day,data:null,error:''});
   try{
    // One full-day snapshot; availability and every other filter are computed locally.
    const data=await api<RoomSnapshot[]>('/rooms/available?'+new URLSearchParams({date:day,periods:'1'}),{signal:controller.signal});
    if(live)setState({day,data,error:''});
   }catch(e){if(live)setState({day,data:null,error:e instanceof Error?e.message:'教室查询失败'})}
   // Schedule after completion so a slow school request cannot overlap the next refresh.
   if(live)timer=setTimeout(load,60000);
  };
  void load();
  return()=>{live=false;controller.abort();if(timer)clearTimeout(timer)};
 },[day,refresh]);
 return state.day===day?state:{day,data:null,error:''};
}
