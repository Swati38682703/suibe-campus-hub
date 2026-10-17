import {useState} from 'react';
import {Link} from 'react-router-dom';
import {Check,EyeOff,RefreshCw,Search,ShieldCheck} from 'lucide-react';
import {api} from './api';
import {Empty,useNotice} from './ui';

type Status='pending'|'normal'|'hidden';
type Review={id:string;course_id:string;course_name:string;teacher:string;semester:string;nickname:string;text:string;overall:number;dimensions:number[];tags:string[];status:Status;created_at:string};
const labels:Record<Status,string>={pending:'待审核',normal:'已通过',hidden:'已隐藏'};
export default function CourseReviewAdmin(){
 const [token,setToken]=useState(''),[rows,setRows]=useState<Review[]|null>(null),[status,setStatus]=useState<Status|'all'>('pending'),[query,setQuery]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState('');
 const notice=useNotice();
 const headers={'X-Admin-Token':token};
 const load=async()=>{setBusy('load');setError('');try{setRows(await api<Review[]>('/admin/course-reviews',{headers}))}catch(e:any){setRows(null);setError(e.message)}finally{setBusy('')}};
 const moderate=async(row:Review,next:Status)=>{setBusy(row.id);setError('');try{await api('/admin/reviews/'+row.id,{method:'PUT',headers,body:JSON.stringify({status:next})});setRows(current=>current?.map(r=>r.id===row.id?{...r,status:next}:r)||null);notice(next==='normal'?'审核通过，点评已公开并计入课程评分':'点评已隐藏，不再公开或计入评分')}catch(e:any){setError(e.message)}finally{setBusy('')}};
 const filtered=(rows||[]).filter(r=>(status==='all'||r.status===status)&&[r.course_name,r.teacher,r.nickname,r.text].join(' ').toLowerCase().includes(query.trim().toLowerCase()));
 return <section className="course-review-admin">
  <div className="panel review-access"><h2><ShieldCheck size={20}/>课程点评审核</h2><p className="muted">这里审核用户真实提交到服务器的课程点评。管理凭证仅在当前页面内存中使用，刷新或离开后需重新填写。</p>
   <form className="filter-row" onSubmit={e=>{e.preventDefault();load()}}><label className="flex">管理员凭证<input required disabled={!!busy} type="password" autoComplete="off" value={token} onChange={e=>{setToken(e.target.value);setRows(null);setError('')}} placeholder="填写服务器配置的 ADMIN_TOKEN"/></label><button className="primary" disabled={!token.trim()||!!busy}>{busy==='load'?'正在加载…':rows?'刷新审核列表':'加载待审核点评'}</button>{rows&&<button type="button" className="secondary" disabled={!!busy} onClick={()=>{setToken('');setRows(null);setError('')}}>退出审核</button>}</form>
   <small>不需要新建账号。凭证由网站维护者在服务器配置中管理，与用户点评的删除凭证不同。</small>
  </div>
  {error&&<div className="error" role="alert">{error}</div>}
  {rows&&<><div className="review-status-tabs" aria-label="点评审核状态">{(['pending','normal','hidden','all'] as const).map(s=><button key={s} aria-pressed={status===s} className={status===s?'selected':''} onClick={()=>setStatus(s)}>{s==='all'?'全部':labels[s]}<span>{rows.filter(r=>s==='all'||r.status===s).length}</span></button>)}</div>
   <div className="demo-admin-toolbar"><label><Search size={17}/><input aria-label="搜索课程点评" placeholder="搜索课程、教师、昵称或点评内容…" value={query} onChange={e=>setQuery(e.target.value)}/></label><button className="secondary" disabled={!!busy} onClick={load}><RefreshCw size={16}/>刷新列表</button></div>
   {filtered.length?filtered.map(r=><article className="panel review-card" key={r.id}><div className="panel-heading"><div><Link to={'/courses/'+r.course_id}><h3>{r.course_name}</h3></Link><p className="muted">{r.teacher} · {r.semester}</p></div><span className={'badge '+(r.status==='normal'?'success':'')}>{labels[r.status]}</span></div><p>{r.nickname} · {r.overall} 星 · {new Date(r.created_at).toLocaleString()}</p><div className="chips">{r.tags.map(t=><span className="badge" key={t}>{t}</span>)}</div><p className="review-body">{r.text||'这位同学只留下了评分。'}</p><p className="muted">{['教学内容','作业体验','给分体验','课程收获'].map((label,i)=>label+' '+r.dimensions[i]+' 星').join(' · ')}</p><div className="toolbar-actions"><button className="primary" disabled={!!busy||r.status==='normal'} onClick={()=>moderate(r,'normal')}><Check size={16}/>{busy===r.id?'正在处理…':'审核通过'}</button><button className="secondary" disabled={!!busy||r.status==='hidden'} onClick={()=>moderate(r,'hidden')}><EyeOff size={16}/>隐藏点评</button><Link className="text-button" to={'/courses/'+r.course_id}>查看课程</Link></div></article>):<Empty>{query?'没有匹配的课程点评。':status==='pending'?'当前没有待审核课程点评。':status==='normal'?'当前没有已通过的课程点评。':status==='hidden'?'当前没有已隐藏的课程点评。':'当前还没有课程点评。'}</Empty>}
  </>}
 </section>;
}
