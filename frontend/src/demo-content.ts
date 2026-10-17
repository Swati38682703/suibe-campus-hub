import {useEffect,useMemo,useState} from 'react';
import {mergeDemoRows,updateDemoPatch,type DemoKind,type DemoPatch} from './demo-content-store';
export type {DemoKind,DemoPatch} from './demo-content-store';
const key=(kind:DemoKind)=>'suibe-demo-content-'+kind;
const event='suibe-demo-content-changed';
function read(kind:DemoKind):DemoPatch[]{
 try{const value=JSON.parse(localStorage.getItem(key(kind))||'[]');return Array.isArray(value)?value.filter(p=>p&&typeof p==='object'&&typeof p.id==='string'):[]}catch{return []}
}
export function saveDemoPatch(kind:DemoKind,patch:DemoPatch){
 localStorage.setItem(key(kind),JSON.stringify(updateDemoPatch(read(kind),patch)));window.dispatchEvent(new Event(event));
}
export function resetDemoContent(kind:DemoKind){localStorage.removeItem(key(kind));window.dispatchEvent(new Event(event))}
export function useDemoContent<T extends {id:string}>(kind:DemoKind,base:T[],includeHidden=false):T[]{
 const [patches,setPatches]=useState(()=>read(kind));
 useEffect(()=>{const refresh=()=>setPatches(read(kind));refresh();window.addEventListener(event,refresh);window.addEventListener('storage',refresh);return()=>{window.removeEventListener(event,refresh);window.removeEventListener('storage',refresh)}},[kind]);
 return useMemo(()=>mergeDemoRows(base,patches,includeHidden),[base,patches,includeHidden]);
}
