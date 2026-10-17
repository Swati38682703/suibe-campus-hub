export type DemoKind='competitions'|'dining'|'announcements';
export interface DemoPatch {id:string;hidden?:boolean;[key:string]:any}
export function mergeDemoRows<T extends {id:string}>(base:T[],patches:DemoPatch[],includeHidden=false):T[]{
 const changes=new Map(patches.map(p=>[p.id,p]));
 const result=base.map(row=>({...row,...changes.get(row.id)}));
 const existing=new Set(base.map(row=>row.id));
 result.push(...patches.filter(p=>!existing.has(p.id)) as T[]);
 return includeHidden?result:result.filter(row=>!(row as T&{hidden?:boolean}).hidden);
}
export function updateDemoPatch(patches:DemoPatch[],patch:DemoPatch):DemoPatch[]{
 const old=patches.find(p=>p.id===patch.id);
 return [...patches.filter(p=>p.id!==patch.id),{...old,...patch}];
}
