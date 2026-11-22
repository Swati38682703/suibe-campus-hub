export type RoomSnapshot={id:string;name:string;building:string;capacity:number;type:string;busy:number[];floor:number|null;[key:string]:any};
export function filterRooms(data:RoomSnapshot[],periods:number[],building:string,capacity:number,query:string,type:string){
 const selected=new Set(periods),needle=query.toLowerCase();
 return data.filter(r=>(!building||r.building===building)&&r.capacity>=capacity&&r.name.toLowerCase().includes(needle)&&(!type||r.type.includes(type)))
  .map(r=>({...r,available:!r.busy.some(p=>selected.has(p))}))
  .sort((a,b)=>Number(!a.available)-Number(!b.available)||a.building.localeCompare(b.building)||(a.floor||0)-(b.floor||0)||a.name.localeCompare(b.name));
}
