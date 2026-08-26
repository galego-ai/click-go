'use client'

import {useEffect,useMemo,useState} from 'react'
import {RefreshCw,Save,TrendingUp} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type Invoice={
 id:string;franchise_id:string;reference_month:string;rides_count:number;gross_ride_value:number;monthly_fee:number;usage_fee:number;matrix_commission:number;total_due:number;due_date:string;status:string;paid_at:string|null
 franchises?:{trade_name:string}|null
}

const brl=(v:any)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))
const num=(v:any)=>new Intl.NumberFormat('pt-BR').format(Number(v||0))
const monthRef=(m:string)=>`${m}-01`
function previousMonth(m:string){const[y,mo]=m.split('-').map(Number);return new Date(Date.UTC(y,mo-2,1)).toISOString().slice(0,7)}
function monthLabel(m:string){return new Intl.DateTimeFormat('pt-BR',{month:'long',year:'numeric'}).format(new Date(`${m}-15T12:00:00`))}

export default function Page(){
 const[settings,setSettings]=useState<any>(null),[tx,setTx]=useState<any[]>([]),[wallets,setWallets]=useState<any[]>([])
 const[invoices,setInvoices]=useState<Invoice[]>([]),[previousInvoices,setPreviousInvoices]=useState<Invoice[]>([])
 const[month,setMonth]=useState(new Date().toISOString().slice(0,7)),[msg,setMsg]=useState(''),[saving,setSaving]=useState(false),[loading,setLoading]=useState(false)

 async function load(){
  setLoading(true);setMsg('')
  const prev=previousMonth(month)
  const[s,t,w,i,pi]=await Promise.all([
   supabase.from('financial_settings').select('*').order('updated_at',{ascending:false}).limit(1).maybeSingle(),
   supabase.from('financial_transactions').select('*,franchises(trade_name),cities(name,state)').order('data_criacao',{ascending:false}).limit(100),
   supabase.from('franchise_wallets').select('*,franchises(trade_name)').order('updated_at',{ascending:false}),
   supabase.from('franchise_invoices').select('id,franchise_id,reference_month,rides_count,gross_ride_value,monthly_fee,usage_fee,matrix_commission,total_due,due_date,status,paid_at,franchises(trade_name)').eq('reference_month',monthRef(month)).order('due_date'),
   supabase.from('franchise_invoices').select('id,franchise_id,reference_month,rides_count,gross_ride_value,monthly_fee,usage_fee,matrix_commission,total_due,due_date,status,paid_at,franchises(trade_name)').eq('reference_month',monthRef(prev)).order('due_date'),
  ])
  const error=s.error||t.error||w.error||i.error||pi.error
  if(error)setMsg(error.message)
  setSettings(s.data||null);setTx(t.data||[]);setWallets(w.data||[]);setInvoices((i.data||[]) as Invoice[]);setPreviousInvoices((pi.data||[]) as Invoice[]);setLoading(false)
 }
 useEffect(()=>{void load()},[month])

 async function save(e:React.FormEvent){
  e.preventDefault();if(!settings)return
  const total=Number(settings.driver_share_percentage||0)+Number(settings.franchise_share_percentage||0)+Number(settings.platform_share_percentage||0)
  if(total>100){setMsg('A soma dos repasses não pode ultrapassar 100%.');return}
  const reason=window.prompt('Alterar regras financeiras globais\n\nInforme a justificativa para auditoria:','')?.trim()
  if(!reason){setMsg('Operação cancelada: a justificativa é obrigatória.');return}
  setSaving(true)
  const{error}=await supabase.rpc('matrix_update_financial_settings',{
   p_card_surcharge_type:settings.card_surcharge_type,
   p_card_surcharge_value:Number(settings.card_surcharge_value||0),
   p_advance_fee_percentage:Number(settings.advance_fee_percentage||0),
   p_driver_share_percentage:Number(settings.driver_share_percentage||0),
   p_franchise_share_percentage:Number(settings.franchise_share_percentage||0),
   p_platform_share_percentage:Number(settings.platform_share_percentage||0),
   p_reason:reason,
  })
  setSaving(false);setMsg(error?error.message:'Regras financeiras atualizadas e registradas na auditoria.');if(!error)void load()
 }

 const paidTx=tx.filter((x:any)=>x.status_pagamento==='PAGO')
 const gross=paidTx.reduce((a:number,x:any)=>a+Number(x.valor_total||0),0)
 const platform=paidTx.reduce((a:number,x:any)=>a+Number(x.valor_plataforma||0),0)
 const franchise=paidTx.reduce((a:number,x:any)=>a+Number(x.valor_franqueado||0),0)
 const today=new Date().toISOString().slice(0,10)
 const invoiceStats=useMemo(()=>{
  const total=invoices.reduce((a,x)=>a+Number(x.total_due||0),0)
  const paid=invoices.filter(x=>x.status==='paid'||x.paid_at).reduce((a,x)=>a+Number(x.total_due||0),0)
  const overdue=invoices.filter(x=>!(x.status==='paid'||x.paid_at)&&Boolean(x.due_date)&&x.due_date<today).reduce((a,x)=>a+Number(x.total_due||0),0)
  const open=Math.max(0,total-paid)
  const previous=previousInvoices.reduce((a,x)=>a+Number(x.total_due||0),0)
  const delta=total-previous
  const deltaPct=previous>0?delta/previous*100:null
  return{total,paid,open,overdue,previous,delta,deltaPct}
 },[invoices,previousInvoices,today])

 return <>
  <div className="topbar"><div><div className="eyebrow">Financeiro da Matriz</div><h1 className="title">Financeiro & Cobranças</h1><p className="subtitle">Faturas das franquias, comparação mensal, regras globais, carteiras e transações centralizadas.</p></div><div className="toolbar"><div className="field"><label>Mês das faturas</label><input className="input" type="month" value={month} onChange={e=>setMonth(e.target.value)}/></div><button className="button secondary" onClick={()=>void load()} disabled={loading}><RefreshCw size={15}/>{loading?'Atualizando...':'Atualizar'}</button></div></div>
  {msg&&<div className="regional-alert">{msg}</div>}

  <div className="grid-3">
   <div className="card"><div className="label">Faturado CLICK-GO · {monthLabel(month)}</div><div className="metric">{brl(invoiceStats.total)}</div><small>{num(invoices.length)} fatura(s)</small></div>
   <div className="card"><div className="label">Recebido / em aberto</div><div className="metric">{brl(invoiceStats.paid)}</div><small>Em aberto: {brl(invoiceStats.open)} · vencido: {brl(invoiceStats.overdue)}</small></div>
   <div className="card"><div className="label">Comparação mês anterior</div><div className="metric">{invoiceStats.delta>=0?'+':''}{brl(invoiceStats.delta)}</div><small><TrendingUp size={13} style={{verticalAlign:'middle'}}/> anterior {brl(invoiceStats.previous)}{invoiceStats.deltaPct===null?' · sem base comparável':` · ${invoiceStats.deltaPct>=0?'+':''}${invoiceStats.deltaPct.toFixed(1)}%`}</small></div>
  </div>

  <div className="section"><div className="section-heading"><div><div className="eyebrow">Cobrança da rede</div><h2>Faturas CLICK-GO · {monthLabel(month)}</h2><p className="subtitle">Somente demonstrativo. Nenhuma cobrança Pix/cartão é criada por esta tela.</p></div></div><div className="table-wrap"><table className="table"><thead><tr><th>Franquia</th><th>Corridas</th><th>Faturamento corridas</th><th>Mensalidade</th><th>Uso</th><th>Comissão</th><th>Total</th><th>Vencimento</th><th>Status</th></tr></thead><tbody>{invoices.length?invoices.map(x=>{const isPaid=x.status==='paid'||Boolean(x.paid_at);const overdue=!isPaid&&x.due_date<today;return <tr key={x.id}><td>{x.franchises?.trade_name||'—'}</td><td>{num(x.rides_count)}</td><td>{brl(x.gross_ride_value)}</td><td>{brl(x.monthly_fee)}</td><td>{brl(x.usage_fee)}</td><td>{brl(x.matrix_commission)}</td><td><strong>{brl(x.total_due)}</strong></td><td>{x.due_date?new Date(x.due_date+'T12:00:00').toLocaleDateString('pt-BR'):'—'}</td><td><span className={'pill '+(isPaid?'green':overdue?'red':'yellow')}>{isPaid?'Pago':overdue?'Vencido':x.status||'Pendente'}</span></td></tr>}):<tr><td colSpan={9} className="empty">Nenhuma fatura materializada neste mês.</td></tr>}</tbody></table></div></div>

  <div className="grid-3"><div className="card"><div className="label">Volume pago das corridas</div><div className="metric">{brl(gross)}</div></div><div className="card"><div className="label">Receita Matriz nas transações</div><div className="metric">{brl(platform)}</div></div><div className="card"><div className="label">Repasse franqueados</div><div className="metric">{brl(franchise)}</div></div></div>

  {settings&&<div className="section"><div className="card"><div className="section-heading"><div><div className="eyebrow">Governança financeira</div><h2>Parametrização global</h2><p className="subtitle">Alterações exigem justificativa e são registradas com valores anteriores e novos na auditoria.</p></div></div><form onSubmit={save}><div className="form-grid"><div className="field"><label>Acréscimo do cartão</label><select className="input" value={settings.card_surcharge_type} onChange={e=>setSettings({...settings,card_surcharge_type:e.target.value})}><option value="percentage">Percentual (%)</option><option value="fixed">Valor fixo (R$)</option></select></div><div className="field"><label>Valor do acréscimo</label><input className="input" type="number" min="0" step="0.01" value={settings.card_surcharge_value} onChange={e=>setSettings({...settings,card_surcharge_value:e.target.value})}/></div><div className="field"><label>Taxa saque antecipado (%)</label><input className="input" type="number" min="0" step="0.01" value={settings.advance_fee_percentage} onChange={e=>setSettings({...settings,advance_fee_percentage:e.target.value})}/></div><div className="field"><label>Motorista (%)</label><input className="input" type="number" min="0" step="0.01" value={settings.driver_share_percentage} onChange={e=>setSettings({...settings,driver_share_percentage:e.target.value})}/></div><div className="field"><label>Franqueado (%)</label><input className="input" type="number" min="0" step="0.01" value={settings.franchise_share_percentage} onChange={e=>setSettings({...settings,franchise_share_percentage:e.target.value})}/></div><div className="field"><label>Matriz (%)</label><input className="input" type="number" min="0" step="0.01" value={settings.platform_share_percentage} onChange={e=>setSettings({...settings,platform_share_percentage:e.target.value})}/></div></div><button className="button" style={{marginTop:14}} disabled={saving}><Save size={15}/>{saving?'Salvando...':'Salvar regras com auditoria'}</button></form></div></div>}

  <div className="section"><h2>Saldos das franquias</h2><div className="table-wrap"><table className="table"><thead><tr><th>Franquia</th><th>Disponível</th><th>Retido</th><th>Atualizado</th></tr></thead><tbody>{wallets.length?wallets.map((w:any)=><tr key={w.id}><td>{w.franchises?.trade_name||'—'}</td><td>{brl(w.available_balance)}</td><td>{brl(w.held_balance)}</td><td>{new Date(w.updated_at).toLocaleString('pt-BR')}</td></tr>):<tr><td colSpan={4} className="empty">Nenhuma carteira.</td></tr>}</tbody></table></div></div>

  <div className="section"><h2>Transações centralizadas</h2><div className="table-wrap"><table className="table"><thead><tr><th>Operação</th><th>Franquia</th><th>Cidade</th><th>Pagamento</th><th>Base</th><th>Cartão</th><th>Motorista</th><th>Franqueado</th><th>Matriz</th><th>Efí</th><th>Antecipação</th><th>Total</th><th>Status</th></tr></thead><tbody>{tx.length?tx.map((x:any)=><tr key={x.id}><td>{x.tipo_operacao}</td><td>{x.franchises?.trade_name||'—'}</td><td>{x.cities?`${x.cities.name}/${x.cities.state}`:'—'}</td><td>{x.tipo_pagamento||'—'}</td><td>{brl(x.valor_corrida_base)}</td><td>{brl(x.taxa_acrescimo_cartao)}</td><td>{brl(x.valor_motorista)}</td><td>{brl(x.valor_franqueado)}</td><td>{brl(x.valor_plataforma)}</td><td>{brl(x.taxa_efi)}</td><td>{brl(x.taxa_antecipacao_saque)}</td><td>{brl(x.valor_total)}</td><td>{x.status_pagamento}</td></tr>):<tr><td colSpan={13} className="empty">Sem movimentação.</td></tr>}</tbody></table></div></div>
 </>
}