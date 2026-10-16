import {createContext,useContext} from 'react';
import {Compass} from 'lucide-react';
export const NoticeContext=createContext<(message: string)=>void>(()=>{});
export const useNotice=()=>useContext(NoticeContext);
export function Empty({children}:{children: React.ReactNode}) {return <div className="empty"><Compass size={28}/><p>{children}</p></div>}
export function PageTitle({eyebrow,title,description,action}:{eyebrow: string;title: string;description: string;action?: React.ReactNode}) {return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>}
