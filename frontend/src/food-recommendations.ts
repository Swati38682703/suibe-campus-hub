export const tasteLabels=['清淡','辛辣','酸甜','咸香','清爽'];
export interface TasteRecord {id:string;score:number;tags:string[];date:string}
export interface FoodChoice {id:string;name:string;restaurant:string;window:string;tag:string;demo:boolean;average:number|null}
export function readTastes():TasteRecord[]{try{return JSON.parse(localStorage.getItem('suibe-food-tastes')||'[]')}catch{return []}}
export function saveTaste(record:TasteRecord){const next=[record,...readTastes().filter(r=>r.id!==record.id)];localStorage.setItem('suibe-food-tastes',JSON.stringify(next));return next}
export function knownTasteTags(dish:FoodChoice,records:TasteRecord[]){const own=records.find(r=>r.id===dish.id);if(own?.tags.length)return own.tags;return /辣/.test(dish.tag)?['辛辣']:/清淡/.test(dish.tag)?['清淡']:[]}
export function recommendFoods(dishes:FoodChoice[],records:TasteRecord[],stamped:string[],mode:'new'|'again',preferred:string[]=[]){
 const eaten=new Set([...stamped,...records.map(r=>r.id)]),ratings=new Map(records.map(r=>[r.id,r]));
 const weights=new Map<string,number>();for(const r of records)for(const tag of r.tags)weights.set(tag,(weights.get(tag)||0)+(r.score-3));for(const tag of preferred)weights.set(tag,(weights.get(tag)||0)+3);
 const windowKey=(d:FoodChoice)=>d.window&&!/待核实|未知|待补充/.test(d.window)?d.restaurant+'|'+d.window:null;
 const visitedWindows=new Set(dishes.filter(d=>eaten.has(d.id)).map(windowKey).filter(Boolean));
 return dishes.filter(d=>!d.demo&&(mode==='new'?!eaten.has(d.id):eaten.has(d.id)&&(ratings.get(d.id)?.score??0)>=4)).map(d=>{
  const tags=knownTasteTags(d,records),affinity=tags.reduce((n,t)=>n+(weights.get(t)||0),0),rating=ratings.get(d.id),newWindow=!!windowKey(d)&&!visitedWindows.has(windowKey(d));
  const reason=mode==='again'?'你给过 '+rating!.score+' 星'+(tags.length?' · '+tags.join('、'):''):newWindow?'还没尝试过这个窗口':tags.some(t=>(weights.get(t)||0)>0)?'符合你的口味偏好':'尚未记录吃过，可以尝尝看';
  return {dish:d,tags,reason,score:mode==='again'?rating!.score*10+affinity:affinity*3+(newWindow?2:0)+(d.average??0)};
 }).sort((a,b)=>b.score-a.score||a.dish.id.localeCompare(b.dish.id)).slice(0,6);
}
