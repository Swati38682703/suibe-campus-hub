export async function api<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch('/api' + path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  const body = await response.json();
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '输入有误，请检查填写内容');
  return body;
}
export const post = <T = any>(path: string, body: unknown, headers = {}) => api<T>(path, {method: 'POST', body: JSON.stringify(body), headers});
export const localDay = (date = new Date()) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
export interface Schedule {id: string; name: string; teacher: string; room: string; day: number; start: number; end: number; weeks: string; semester: string}
export function readSchedule(): Schedule[] {try {return JSON.parse(localStorage.getItem('suibe-timetable') || '[]');} catch {return [];}}
export function parseWeeks(value: string): number[] {
  const result: number[]=[];
  if (!/^\d+(?:-\d+)?(?:[,，]\d+(?:-\d+)?)*$/.test(value.trim())) throw new Error('周次格式如 1-16 或 1-8,10-16');
  for (const part of value.split(/[,，]/)) {
    const [a,b=a]=part.split('-').map(Number);
    if (a<1 || b>30 || a>b) throw new Error('周次范围须在 1–30 之间');
    for(let i=a;i<=b;i++) result.push(i);
  }
  return [...new Set(result)];
}
export function validateSchedule(rows: any[]): Schedule[] {
  if (!Array.isArray(rows) || rows.length>100) throw new Error('课表应为不超过 100 条记录的数组');
  const ids=new Set<string>();
  return rows.map((r,i) => {
    if (typeof r.name!=='string' || !r.name.trim() || r.name.length>100 || !Number.isInteger(r.day) || r.day<1 || r.day>7 || !Number.isInteger(r.start) || !Number.isInteger(r.end) || r.start<1 || r.end>14 || r.start>r.end) throw new Error(`第 ${i+1} 条课程字段有误`);
    const weeks=String(r.weeks||'1-20'); parseWeeks(weeks);
    const id=String(r.id||crypto.randomUUID());
    if(ids.has(id))throw new Error('课表记录 ID 重复');
    ids.add(id);
    return {id,name:r.name.trim(),day:r.day,start:r.start,end:r.end,room:String(r.room||'').slice(0,50),teacher:String(r.teacher||'').slice(0,50),weeks,semester:String(r.semester||'2026-2027-1')};
  });
}
export function conflicts(a: Schedule,b: Schedule) {return a.id!==b.id && a.semester===b.semester && a.day===b.day && a.start<=b.end && a.end>=b.start && parseWeeks(a.weeks).some(w=>parseWeeks(b.weeks).includes(w));}
export function download(name: string, value: string, type='application/json') {const url=URL.createObjectURL(new Blob([value],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();URL.revokeObjectURL(url);}
