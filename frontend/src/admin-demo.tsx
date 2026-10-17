import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {ArrowRight,Bell,Eye,EyeOff,Plus,RotateCcw,Save,Search,ShieldCheck,Trophy,Utensils,Users} from 'lucide-react';
import {api,localDay} from './api';
import {COMPETITIONS} from './competitions-data';
import {useDemoContent,saveDemoPatch,resetDemoContent,type DemoKind,type DemoPatch} from './demo-content';
import {PageTitle,useNotice,Empty} from './ui';
import './admin-demo.css';
type Row=DemoPatch;
type Field={key:string;label:string;type?:string;required?:boolean;options?:[string,string][];wide?:boolean};
const sections=[{id:'competitions' as const,label:'赛事管理',icon:Trophy,to:'/competitions'},{id:'dining' as const,label:'食堂管理',icon:Utensils,to:'/dining'},{id:'teachers' as const,label:'教师管理',icon:Users,to:'/teachers'},{id:'announcements' as const,label:'公告管理',icon:Bell,to:'/announcements'}];
const fields:Record<DemoKind,Field[]>={
 competitions:[{key:'title',label:'赛事名称',required:true,wide:true},{key:'scope',label:'赛事范围',options:[['campus','校内赛事'],['major','大型赛事']]},{key:'field',label:'比赛方向',required:true},{key:'deadline',label:'报名截止日期',type:'date'},{key:'deadlineTime',label:'截止时刻',type:'time'},{key:'audience',label:'参赛对象',required:true,wide:true},{key:'team',label:'组队与参赛形式',required:true,wide:true},{key:'summary',label:'赛事简介',type:'textarea',required:true,wide:true},{key:'schedule',label:'赛程安排',type:'textarea',wide:true},{key:'notice',label:'参赛须知',type:'textarea',wide:true},{key:'source',label:'信息来源',wide:true},{key:'sourceUrl',label:'原文链接（网页或站内 PDF）',wide:true},{key:'organizer',label:'组织单位',wide:true}],
 dining:[{key:'name',label:'菜品名称',required:true},{key:'restaurant',label:'餐厅',options:[['一食堂','一食堂'],['文贸餐厅','文贸餐厅']]},{key:'window',label:'楼层 / 窗口',required:true},{key:'price',label:'价格（元，可留空）',type:'number'},{key:'emoji',label:'菜品图标',required:true},{key:'tag',label:'口味 / 分类'},{key:'description',label:'菜品介绍',type:'textarea',wide:true},{key:'source_url',label:'信息来源链接',wide:true}],
 teachers:[{key:'name',label:'教师姓名',required:true},{key:'pinyin',label:'拼音 / 首字母',required:true},{key:'department',label:'所属学院',required:true},{key:'title',label:'职称',required:true},{key:'email',label:'公开工作邮箱',type:'email'},{key:'office',label:'办公地点'},{key:'research',label:'研究方向',type:'textarea',wide:true},{key:'source',label:'信息来源',wide:true}],
 announcements:[{key:'title',label:'公告标题',required:true,wide:true},{key:'department',label:'发布部门',required:true},{key:'date',label:'发布日期',type:'date',required:true},{key:'content',label:'公告内容',type:'textarea',required:true,wide:true},{key:'pinned',label:'置顶状态',options:[['false','普通公告'],['true','置顶公告']]},{key:'source',label:'信息来源'}],
};
function newRow(kind:DemoKind):Row{
 const common={id:'preview-'+kind+'-'+crypto.randomUUID(),hidden:false};
 if(kind==='competitions')return {...common,title:'',scope:'campus',level:'校内赛事',field:'创新创业',audience:'本校学生',team:'以通知为准',summary:'',schedule:'待公布',notice:'学校展示用的演示内容，不代表正式通知。',source:'展示演示',sourceUrl:'/competitions',organizer:'校园服务助手',checked:localDay()};
 if(kind==='teachers')return {...common,name:'',pinyin:'',department:'',title:'讲师',email:'',office:'',research:'',source:'管理员演示资料，未经学校核实',updated_at:localDay()};
 if(kind==='dining')return {...common,name:'',restaurant:'一食堂',window:'窗口待核实',price:null,emoji:'🍚',tag:'家常',description:'展示演示菜品',demo:false,semester:'2026-2027-1',count:0,average:null,reviews:[]};
 return {...common,title:'',department:'校园服务助手',date:localDay(),content:'',pinned:false,source:'管理员演示发布'};
}
export default function AdminDemo(){
 const notice=useNotice(),[kind,setKind]=useState<DemoKind>('competitions'),[query,setQuery]=useState(''),[draft,setDraft]=useState<Row|null>(null),[baseDining,setBaseDining]=useState<Row[]>([]),[baseAnnouncements,setBaseAnnouncements]=useState<Row[]>([]),[baseTeachers,setBaseTeachers]=useState<Row[]>([]),[error,setError]=useState('');
 const contests=useDemoContent('competitions',COMPETITIONS,true) as Row[],dining=useDemoContent('dining',baseDining,true),announcements=useDemoContent('announcements',baseAnnouncements,true),teachers=useDemoContent('teachers',baseTeachers,true);
 const load=()=>{setError('');Promise.all([api('/dining'),api('/announcements'),api('/teachers')]).then(([d,a,t])=>{setBaseDining(d);setBaseAnnouncements(a);setBaseTeachers(t)}).catch(e=>setError(e.message))};
 useEffect(load,[]);
 const rows=kind==='competitions'?contests:kind==='dining'?dining.filter(d=>!d.demo):kind==='teachers'?teachers:announcements;
 const section=sections.find(s=>s.id===kind)!;
 const filtered=rows.filter(r=>[r.title,r.name,r.restaurant,r.department].join(' ').includes(query.trim()));
 const changeKind=(value:DemoKind)=>{setKind(value);setDraft(null);setQuery('')};
 const save=(e:React.FormEvent)=>{e.preventDefault();if(!draft)return;
  const value={...draft};
  for(const key of ['sourceUrl','source_url'])if(value[key]&&!/^https?:\/\//i.test(value[key])&&!/^\/(?!\/)/.test(value[key])){notice('来源链接请使用 http、https 或站内路径');return}
  if(kind==='competitions'){
   value.checked=localDay();value.level=value.scope==='campus'?'校内赛事':'大型赛事';
   if(!value.deadline){value.deadline='';value.deadlineTime=''}
   if(value.endedOn&&value.deadline&&value.endedOn<value.deadline)value.endedOn='';
   value.sourceFormat=value.sourceUrl?.split('?')[0].endsWith('.pdf')?'pdf':null;
   // A new source link replaces the old button destination as well.
   if(value.sourceUrl!==rows.find(r=>r.id===value.id)?.sourceUrl)value.website=value.sourceUrl;
  }
  if(kind==='dining'){value.price=value.price===''||value.price===null?null:Number(value.price);if(value.price!==null&&(!Number.isFinite(value.price)||value.price<0)){notice('价格须为非负数字或留空');return}}
  if(kind==='teachers')value.updated_at=localDay();
  if(kind==='announcements')value.pinned=value.pinned===true||value.pinned==='true';
  try{saveDemoPatch(kind,value);setDraft(null);notice('演示内容已保存，切回用户视图即可查看')}catch{notice('浏览器保存失败，请检查存储空间或隐私模式')}
 };
 return <div className="demo-admin"><PageTitle eyebrow="ADMIN · PRESENTATION MODE" title="管理员工作台" description="把校园信息，轻松打理好。" action={<Link className="primary" to={section.to}><Eye size={16}/>预览用户页面<ArrowRight size={15}/></Link>}/>
  <section className="demo-admin-banner"><ShieldCheck size={26}/><div><strong>学校展示模式 · 无需登录</strong><p>可演示新增、修改、隐藏内容；保存后用户视图即时更新。修改仅存于当前浏览器，不会写入服务器。</p></div></section>
  <div className="demo-admin-stats">{sections.map(s=><button key={s.id} className={kind===s.id?'active':''} onClick={()=>changeKind(s.id)}><s.icon size={23}/><strong>{s.label}</strong><span>{(s.id==='competitions'?contests:s.id==='dining'?dining.filter(d=>!d.demo):s.id==='teachers'?teachers:announcements).filter(r=>!r.hidden).length} 项显示中</span></button>)}</div>
  {error&&<div className="error" role="alert">在线资料加载失败：{error} <button className="text-button" onClick={load}>重新加载</button>。仍可演示新增内容。</div>}
  <div className="demo-admin-toolbar"><label><Search size={17}/><input aria-label="搜索管理内容" value={query} onChange={e=>setQuery(e.target.value)} placeholder="搜索标题、菜品、教师或学院…"/></label><button className="primary" onClick={()=>setDraft(newRow(kind))}><Plus size={16}/>新增{section.label.slice(0,2)}</button><button className="secondary" onClick={()=>{try{resetDemoContent(kind);setDraft(null);notice('本栏目已恢复原始内容，课表与集邮照片不会删除')}catch{notice('重置失败，请检查浏览器存储权限')}}}><RotateCcw size={15}/>重置本栏演示</button></div>
  {draft?<section className="panel demo-editor"><div className="panel-heading"><h2>{rows.some(r=>r.id===draft.id)?'编辑内容':'新增内容'}</h2><button className="text-button" onClick={()=>setDraft(null)}>取消编辑</button></div><form onSubmit={save}><div className="demo-editor-grid">{fields[kind].map(f=><label key={f.key} className={f.wide?'wide':''}>{f.label}{f.options?<select value={String(draft[f.key]??'')} onChange={e=>setDraft({...draft,[f.key]:e.target.value})}>{f.options.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>:f.type==='textarea'?<textarea required={f.required} maxLength={10000} value={String(draft[f.key]??'')} onChange={e=>setDraft({...draft,[f.key]:e.target.value})}/>:<input required={f.required} type={f.type||'text'} min={f.type==='number'?0:undefined} step={f.type==='number'?'0.01':undefined} maxLength={1000} value={String(draft[f.key]??'')} onChange={e=>setDraft({...draft,[f.key]:e.target.value})}/>}</label>)}</div><div className="demo-editor-actions"><button className="primary"><Save size={16}/>保存演示修改</button><small>保存后可切换到用户视图，展示修改效果。</small></div></form></section>:<section className="panel demo-management-list"><div className="panel-heading"><h2>{section.label}</h2><span className="muted">{filtered.length} 项 · 含已隐藏内容</span></div>{filtered.length?filtered.map(r=><article key={r.id}><div><h3>{kind==='teachers'?r.name:r.title||r.name}<span className={'badge '+(r.hidden?'':'success')}>{r.hidden?'已隐藏':'显示中'}</span></h3><p>{r.restaurant?[r.restaurant,r.window].join(' · '):r.deadline?'报名截止 '+r.deadline+(r.deadlineTime?' '+r.deadlineTime:''):r.department||r.field||'赛事记录'}</p></div><div><button className="secondary" aria-label={'编辑'+(kind==='teachers'?r.name:r.title||r.name)} onClick={()=>setDraft({...r})}>编辑</button><button className="text-button" aria-label={(r.hidden?'显示':'隐藏')+(kind==='teachers'?r.name:r.title||r.name)} onClick={()=>{try{saveDemoPatch(kind,{id:r.id,hidden:!r.hidden});notice(r.hidden?'已恢复显示':'已在用户视图中隐藏')}catch{notice('保存失败，请检查浏览器存储权限')}}}>{r.hidden?<Eye size={16}/>:<EyeOff size={16}/>}<span>{r.hidden?'显示':'隐藏'}</span></button></div></article>):<Empty>暂无内容，点击新增开始演示。</Empty>}</section>}
  <p className="muted">此入口为展示角色，任何人都可切换；不代表真实管理员身份。重置仅清除本栏目演示编辑，不删除个人课表、照片和收藏。</p>
 </div>
}
