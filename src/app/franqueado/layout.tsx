'use client'

import Link from 'next/link'
import {useEffect,useState} from 'react'
import {usePathname} from 'next/navigation'
import RoleGate from '@/components/RoleGate'
import {supabase} from '@/lib/supabase'

type NavItem={href:string;label:string;permission?:string|string[]}
const core:NavItem[]=[
 {href:'/franqueado',label:'Início'},
 {href:'/franqueado/operacao',label:'Corridas',permission:'operation'},
 {href:'/franqueado/cadastros',label:'Pessoas',permission:['drivers','users']},
 {href:'/franqueado/pagamentos',label:'Financeiro',permission:'finance'},
 {href:'/franqueado/suporte',label:'Suporte',permission:'support'},
]
const more:NavItem[]=[
 {href:'/franqueado/mapa',label:'Mapa ao vivo',permission:'operation'},
 {href:'/franqueado/categorias',label:'Tarifas e preços',permission:'pricing'},
 {href:'/franqueado/equipe',label:'Minha equipe',permission:'settings'},
 {href:'/franqueado/anuncios',label:'Promoções e anúncios',permission:'marketing'},
 {href:'/franqueado/configuracoes',label:'Configurações locais',permission:['settings','pricing','finance']},
 {href:'/franqueado/documentos',label:'Documentos de motoristas',permission:'drivers'},
 {href:'/franqueado/cancelamentos',label:'Cancelamentos',permission:'operation'},
 {href:'/franqueado/repasse',label:'Repasses',permission:'finance'},
 {href:'/franqueado/carteiras',label:'Carteiras',permission:'finance'},
 {href:'/franqueado/seguranca',label:'Segurança',permission:['operation','support']},
 {href:'/franqueado/taximetros',label:'Taxímetros',permission:'operation'},
 {href:'/franqueado/motoristas-categorias',label:'Categorias de motoristas',permission:['drivers','pricing']},
]

export default function FranchiseLayout({children}:{children:React.ReactNode}){
 const pathname=usePathname(),[role,setRole]=useState('franchise_admin'),[staffRole,setStaffRole]=useState(''),[permissions,setPermissions]=useState<Record<string,boolean>>({}),[configVersion,setConfigVersion]=useState(0),[license,setLicense]=useState('')
 useEffect(()=>{let alive=true;(async()=>{const{data:{user}}=await supabase.auth.getUser();if(!user||!alive)return;const r=String(user.app_metadata?.role||'franchise_admin');setRole(r);const{data:p}=await supabase.from('profiles').select('franchise_id').eq('id',user.id).maybeSingle();const fid=String(p?.franchise_id||user.app_metadata?.franchise_id||'');if(r==='operator'){const{data:s}=await supabase.from('franchise_staff_permissions').select('staff_role,permissions').eq('profile_id',user.id).maybeSingle();if(s){setStaffRole(String(s.staff_role||''));setPermissions((s.permissions||{}) as Record<string,boolean>)}}if(fid){const{data:c}=await supabase.rpc('get_app_configuration_state',{p_franchise_id:fid,p_city_id:null});if(c){setConfigVersion(Number(c.version||0));setLicense(String(c.license_status||''))}}})();return()=>{alive=false}},[])
 if(pathname==='/franqueado/login'||pathname==='/franqueado/trocar-senha-temporaria')return <>{children}</>
 const can=(item:NavItem)=>{if(role==='franchise_admin')return true;if(!item.permission)return true;const list=Array.isArray(item.permission)?item.permission:[item.permission];return list.some(p=>permissions[p]===true)}
 const visibleCore=core.filter(can),visibleMore=more.filter(can),active=(href:string)=>pathname===href||pathname.startsWith(href+'/'),moreOpen=visibleMore.some(item=>active(item.href)),title=role==='franchise_admin'?'Franqueado':staffRole==='manager'?'Gerente':staffRole==='financial'?'Financeiro':staffRole==='support'?'Suporte':staffRole==='marketing'?'Marketing':'Operador'
 return <RoleGate role={['franchise_admin','operator']} loginPath="/franqueado/login"><div className="simple-shell"><aside className="simple-sidebar"><Link href="/franqueado" className="simple-brand"><span className="simple-brand-mark">CG</span><div><strong>CLICK-GO</strong><small>{title}</small></div></Link><nav className="simple-nav">{visibleCore.map(item=><Link key={item.href} href={item.href} className={active(item.href)?'active':''}>{item.label}</Link>)}{visibleMore.length>0&&<details className="simple-more" open={moreOpen}><summary>Mais</summary><div>{visibleMore.map(item=><Link key={item.href} href={item.href} className={active(item.href)?'active':''}>{item.label}</Link>)}</div></details>}</nav><div style={{marginTop:'auto',padding:'14px 10px 4px',borderTop:'1px solid #e7e9ee'}}><div style={{fontSize:10,fontWeight:800,color:'#1b8f4b'}}>● Sistema sincronizado</div><div style={{fontSize:10,color:'#8f949c',marginTop:5}}>Configuração v{configVersion} · {license||'verificando licença'}</div></div></aside><main className="simple-main">{children}</main></div></RoleGate>
}
