'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { supabase } from '@/lib/supabase'
import DriverRideHistory from '@/components/DriverRideHistory'

type City = { id: string; name: string; state: string }
type Driver = { id:string; status:string; online:boolean; rating:number|string; city_id:string|null; franchise_id:string|null; rejection_reason:string|null }
type Profile = { id:string; full_name:string|null; email:string|null; phone:string|null; role:string; city_id:string|null; franchise_id:string|null }
type Doc = { id:string; document_type:string; file_path:string; status:string; rejection_reason:string|null; created_at:string }
type Vehicle = { id:string; make:string; model:string; year:number|null; plate:string; color:string|null; vehicle_type:string|null; active:boolean }

const menu = ['Início', 'Corridas', 'Ganhos', 'Carteira', 'Documentos', 'Meu veículo', 'Avaliações', 'Ajuda e suporte', 'Meu perfil']
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}
const docTypes=[['cnh_frente','CNH - frente'],['cnh_verso','CNH - verso'],['selfie_cnh','Selfie segurando a CNH'],['crlv','CRLV do veículo'],['comprovante_residencia','Comprovante de residência']]

export default function DriverAppPage() {
  const [cities, setCities] = useState<City[]>([])
  const [active, setActive] = useState('Início')
  const [authMode,setAuthMode]=useState<'login'|'register'>('login')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [profile,setProfile]=useState<Profile|null>(null)
  const [driver,setDriver]=useState<Driver|null>(null)
  const [docs,setDocs]=useState<Doc[]>([])
  const [vehicles,setVehicles]=useState<Vehicle[]>([])
  const [docType,setDocType]=useState('cnh_frente')
  const [file,setFile]=useState<File|null>(null)

  useEffect(() => {
    supabase.from('cities').select('id,name,state').eq('active', true).order('name').then(({data,error}) => {
      setCities((data || []) as City[])
      if(error) setMessage('Não foi possível carregar as cidades: '+error.message)
    })
    restoreSession()
    const {data:listener}=supabase.auth.onAuthStateChange((_event,session)=>{if(!session){setProfile(null);setDriver(null);setDocs([]);setVehicles([])}})
    return()=>listener.subscription.unsubscribe()
  }, [])

  async function restoreSession(){const {data:{user}}=await supabase.auth.getUser();if(user) await loadDriver(user.id)}

  async function loadDriver(userId?:string){
    setLoading(true);setMessage('')
    try{
      const id=userId || (await supabase.auth.getUser()).data.user?.id;if(!id)return
      const {data:p,error:pe}=await supabase.from('profiles').select('id,full_name,email,phone,role,city_id,franchise_id').eq('id',id).single();if(pe)throw pe
      if(!p || p.role!=='driver'){await supabase.auth.signOut();throw new Error('Esta conta não é de motorista.')}
      const [{data:d,error:de},{data:documents,error:doce},{data:v,error:ve}]=await Promise.all([
        supabase.from('drivers').select('id,status,online,rating,city_id,franchise_id,rejection_reason').eq('id',id).single(),
        supabase.from('driver_documents').select('id,document_type,file_path,status,rejection_reason,created_at').eq('driver_id',id).order('created_at',{ascending:false}),
        supabase.from('vehicles').select('id,make,model,year,plate,color,vehicle_type,active').eq('driver_id',id).order('created_at',{ascending:false})
      ])
      if(de)throw de;if(doce)throw doce;if(ve)throw ve
      setProfile(p as Profile);setDriver(d as Driver);setDocs((documents||[]) as Doc[]);setVehicles((v||[]) as Vehicle[])
    }catch(e:any){setMessage(e.message||'Erro ao carregar cadastro do motorista.')}finally{setLoading(false)}
  }

  async function login(e:FormEvent<HTMLFormElement>){e.preventDefault();setLoading(true);setMessage('Entrando...');const data=new FormData(e.currentTarget);const {data:auth,error}=await supabase.auth.signInWithPassword({email:String(data.get('email')||'').trim(),password:String(data.get('password')||'')});if(error){setMessage(error.message);setLoading(false);return}await loadDriver(auth.user.id)}

  async function register(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();setLoading(true);setMessage('');const data = new FormData(e.currentTarget);const cityId=String(data.get('city_id')||'')
    if(!cityId){setLoading(false);setMessage('Escolha a cidade onde deseja trabalhar.');return}
    const { data:auth, error } = await supabase.auth.signUp({email:String(data.get('email')||'').trim(),password:String(data.get('password')||''),options:{data:{app_role:'driver',requested_city_id:cityId,full_name:String(data.get('full_name')||'').trim(),phone:String(data.get('phone')||'').trim(),cpf:String(data.get('cpf')||'').trim(),cnh_number:String(data.get('cnh_number')||'').trim(),cnh_category:String(data.get('cnh_category')||'').trim(),vehicle_plate:String(data.get('vehicle_plate')||'').trim(),vehicle_make:String(data.get('vehicle_make')||'').trim(),vehicle_model:String(data.get('vehicle_model')||'').trim(),vehicle_year:String(data.get('vehicle_year')||'').trim(),vehicle_color:String(data.get('vehicle_color')||'').trim(),vehicle_type:String(data.get('vehicle_type')||'').trim()}}})
    setLoading(false);if(error){setMessage(error.message);return}if(auth.session){await loadDriver(auth.user?.id);setMessage('Cadastro criado. Envie agora seus documentos para análise.')}else setMessage('Cadastro enviado. Confirme seu e-mail e depois entre no App Motorista para enviar os documentos. O franqueado da cidade escolhida fará a aprovação.')
  }

  async function uploadDocument(e:FormEvent){
    e.preventDefault();if(!file||!profile){setMessage('Selecione um arquivo.');return}
    setLoading(true);setMessage('Enviando documento...')
    try{
      const ext=(file.name.split('.').pop()||'bin').toLowerCase().replace(/[^a-z0-9]/g,'');const path=`${profile.id}/${docType}-${Date.now()}.${ext}`
      const {error:up}=await supabase.storage.from('driver-documents').upload(path,file,{upsert:false,contentType:file.type||undefined});if(up)throw up
      const {error:db}=await supabase.from('driver_documents').insert({driver_id:profile.id,document_type:docType,file_path:path,status:'pending'});if(db){await supabase.storage.from('driver-documents').remove([path]);throw db}
      setFile(null);const element=document.getElementById('driver-document-file') as HTMLInputElement|null;if(element)element.value='';setMessage('Documento enviado. O franqueado poderá analisá-lo agora.');await loadDriver(profile.id)
    }catch(e:any){setMessage(e.message||'Erro ao enviar documento.')}finally{setLoading(false)}
  }

  async function logout(){await supabase.auth.signOut();setMessage('Sessão encerrada.');setAuthMode('login');setActive('Início')}

  const cityName=useMemo(()=>{const c=cities.find(x=>x.id===profile?.city_id);return c?`${c.name}/${c.state}`:'-'},[cities,profile])
  const approvedDocs=docs.filter(d=>d.status==='approved').length,pendingDocs=docs.filter(d=>d.status==='pending').length,rejectedDocs=docs.filter(d=>d.status==='rejected').length

  if(!profile) return <main style={{minHeight:'100vh',background:'#080808',color:'#f8fafc',padding:24}}><div style={{maxWidth:760,margin:'0 auto'}}><div className="eyebrow">App Motorista</div><h1 className="title">CLICK-GO Motorista</h1><p className="subtitle">Cadastre-se para trabalhar ou entre para acompanhar sua aprovação e enviar documentos.</p><div style={{display:'flex',gap:8,margin:'22px 0 14px'}}><button style={{...btn,background:authMode==='login'?'#ffd400':'#222',color:authMode==='login'?'#000':'#fff'}} onClick={()=>setAuthMode('login')}>Entrar</button><button style={{...btn,background:authMode==='register'?'#ffd400':'#222',color:authMode==='register'?'#000':'#fff'}} onClick={()=>setAuthMode('register')}>Criar cadastro</button></div><section style={box}>{authMode==='login'?<form onSubmit={login} style={{display:'grid',gap:12}}><h2 style={{marginTop:0}}>Entrar como motorista</h2><input name="email" required type="email" placeholder="E-mail" style={input}/><input name="password" required type="password" placeholder="Senha" style={input}/><button style={btn} disabled={loading}>{loading?'Entrando...':'Entrar'}</button></form>:<form onSubmit={register} style={{display:'grid',gap:12}}><h2 style={{marginTop:0}}>Cadastro do motorista</h2><p className="subtitle">Escolha a cidade onde deseja trabalhar. Seu cadastro será encaminhado automaticamente ao franqueado responsável.</p><select name="city_id" required style={input} defaultValue=""><option value="" disabled>{cities.length?'Escolha a cidade de atuação':'Carregando cidades...'}</option>{cities.map(c=><option key={c.id} value={c.id}>{c.name} - {c.state}</option>)}</select>{!cities.length&&<div style={{color:'#fca5a5',fontSize:13}}>Nenhuma cidade ativa disponível para cadastro neste momento.</div>}<input name="full_name" required placeholder="Nome completo" style={input}/><input name="phone" required placeholder="Telefone / WhatsApp" style={input}/><input name="cpf" required placeholder="CPF" style={input}/><input name="cnh_number" required placeholder="Número da CNH" style={input}/><input name="cnh_category" required placeholder="Categoria da CNH" style={input}/><div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input name="vehicle_plate" required placeholder="Placa" style={input}/><input name="vehicle_type" placeholder="Tipo do veículo" style={input}/></div><div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input name="vehicle_make" placeholder="Marca" style={input}/><input name="vehicle_model" placeholder="Modelo" style={input}/></div><div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}><input name="vehicle_year" type="number" placeholder="Ano" style={input}/><input name="vehicle_color" placeholder="Cor" style={input}/></div><input name="email" required type="email" placeholder="E-mail" style={input}/><input name="password" required type="password" minLength={6} placeholder="Senha (mínimo 6 caracteres)" style={input}/><button style={btn} disabled={loading||!cities.length}>{loading?'Enviando...':'Enviar cadastro para aprovação'}</button></form>}{message&&<p style={{marginTop:14,color:'#ffe66b'}}>{message}</p>}</section></div></main>

  return <main style={{minHeight:'100vh',background:'#080808',color:'#f8fafc',padding:20}}><div className="topbar"><div><div className="eyebrow">App Motorista</div><h1 className="title">CLICK-GO Motorista</h1><p className="subtitle">{profile.full_name||profile.email} · {cityName}</p></div><button style={{...btn,background:'#222',color:'#fff'}} onClick={logout}>Sair</button></div><div style={{display:'grid',gridTemplateColumns:'230px 1fr',gap:16,alignItems:'start'}}><aside style={{...box,padding:10}}>{menu.map(item=><button key={item} onClick={()=>setActive(item)} style={{display:'block',width:'100%',textAlign:'left',padding:'12px',marginBottom:6,border:0,borderRadius:10,cursor:'pointer',fontWeight:700,background:active===item?'#ffd400':'#1d1d1d',color:active===item?'#000':'#fff'}}>{item}</button>)}</aside><section style={box}><div className="eyebrow">{active}</div>
   {active==='Início'&&<><h2>Status do cadastro</h2><div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:12,marginTop:14}}><div style={box}><div className="label">Situação</div><div className="metric" style={{fontSize:22}}>{driver?.status||'-'}</div></div><div style={box}><div className="label">Documentos aprovados</div><div className="metric">{approvedDocs}</div></div><div style={box}><div className="label">Em análise</div><div className="metric">{pendingDocs}</div></div><div style={box}><div className="label">Reprovados</div><div className="metric">{rejectedDocs}</div></div></div>{driver?.status==='pending'&&<p style={{color:'#fde68a',marginTop:16}}>Seu cadastro está aguardando aprovação do franqueado. Envie todos os documentos solicitados na aba Documentos.</p>}{driver?.status==='approved'&&<p style={{color:'#86efac',marginTop:16}}>Cadastro aprovado. Use “Operação e corridas” no topo para ficar online e receber chamadas.</p>}{driver?.status==='rejected'&&<p style={{color:'#fca5a5',marginTop:16}}>Cadastro reprovado. {driver.rejection_reason||'Entre em contato com o suporte da sua cidade.'}</p>}</>}
   {active==='Corridas'&&<><h2>Histórico de corridas</h2><p className="subtitle">Inclui as coordenadas de origem, destino, chegada ao embarque, início, fim e todos os pontos GPS registrados durante o trajeto.</p><DriverRideHistory/></>}
   {active==='Documentos'&&<><h2>Meus documentos</h2><p className="subtitle">Envie fotos legíveis ou PDF. Os arquivos ficam privados e somente você, o franqueado responsável e a matriz podem acessar.</p><form onSubmit={uploadDocument} style={{display:'grid',gridTemplateColumns:'1fr 1.5fr auto',gap:10,alignItems:'end',marginTop:18}}><label style={{display:'grid',gap:6,fontSize:13}}>Tipo<select value={docType} onChange={e=>setDocType(e.target.value)} style={input}>{docTypes.map(([v,n])=><option key={v} value={v}>{n}</option>)}</select></label><label style={{display:'grid',gap:6,fontSize:13}}>Arquivo<input id="driver-document-file" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" required onChange={e=>setFile(e.target.files?.[0]||null)} style={input}/></label><button style={btn} disabled={loading}>{loading?'Enviando...':'Enviar documento'}</button></form><div style={{display:'grid',gap:10,marginTop:18}}>{docs.map(d=><div key={d.id} style={{...box,display:'grid',gridTemplateColumns:'1.5fr 1fr 1fr',gap:12,alignItems:'center'}}><div><b>{docTypes.find(x=>x[0]===d.document_type)?.[1]||d.document_type}</b><div style={{fontSize:12,color:'#9ca3af'}}>{new Date(d.created_at).toLocaleString('pt-BR')}</div></div><span>{d.status}</span><span style={{color:d.status==='rejected'?'#fca5a5':'#9ca3af'}}>{d.rejection_reason||'Sem observações'}</span></div>)}{!docs.length&&<div style={box}>Você ainda não enviou documentos.</div>}</div></>}
   {active==='Meu veículo'&&<><h2>Meu veículo</h2>{vehicles.map(v=><div key={v.id} style={box}><b>{v.make} {v.model}</b><div style={{color:'#9ca3af',marginTop:6}}>{v.plate} · {v.year||'-'} · {v.color||'-'} · {v.vehicle_type||'Veículo'}</div></div>)}{!vehicles.length&&<p className="subtitle">Nenhum veículo cadastrado.</p>}</>}
   {active==='Meu perfil'&&<><h2>Meu perfil</h2><div style={box}><div><b>{profile.full_name||'Motorista'}</b></div><div style={{color:'#9ca3af',marginTop:8}}>{profile.email}<br/>{profile.phone}<br/>{cityName}</div></div></>}
   {!['Início','Corridas','Documentos','Meu veículo','Meu perfil'].includes(active)&&<><h2>{active}</h2><p className="subtitle">Esta área será liberada conforme o cadastro e a operação do motorista forem aprovados.</p></>}
   {message&&<p style={{marginTop:14,color:'#ffe66b'}}>{message}</p>}
  </section></div></main>
}
