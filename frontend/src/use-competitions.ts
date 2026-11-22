import {useEffect,useState} from 'react';
import {api} from './api';
import {COMPETITIONS,type Competition} from './competitions-data';
export type CompetitionSync={lastCompleted?:string;lastSuccessfulCheck?:string;status?:string;autoCount?:number;importedCount?:number;intervalHours?:number;wechat?:string;scheduleNote?:string;sources?:{name:string;url:string;status:string}[]};
export function useCompetitions(){
 const [rows,setRows]=useState<Competition[]>(COMPETITIONS),[sync,setSync]=useState<CompetitionSync|null>(null),[error,setError]=useState('');
 useEffect(()=>{
  let live=true;
  const load=async()=>{
   try{
    const rows=await api<Competition[]>('/competitions');
    if(!Array.isArray(rows))throw new Error('赛事服务返回格式异常');
    if(live){setRows(rows);setError('')}
   }catch{if(live)setError('暂时无法读取更新，当前保留上次资料或随版本提供的赛事。')}
   try{const status=await api<CompetitionSync>('/competitions/sync-status');if(live)setSync(status)}catch{}
  };
  window.addEventListener('suibe-competitions-updated',load);
  void load();const timer=window.setInterval(load,60000);
  return()=>{window.removeEventListener('suibe-competitions-updated',load);live=false;window.clearInterval(timer)};
 },[]);
 return {rows,sync,error};
}
