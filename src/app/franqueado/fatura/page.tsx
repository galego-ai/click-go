'use client'

import {useEffect,useMemo,useState} from 'react'
import {CalendarDays,Copy,CreditCard,ExternalLink,QrCode,RefreshCw,TrendingUp} from 'lucide-react'
import {supabase} from '@/lib/supabase'

type Adjustment={id:string;type:string;description:string;amount:number;created_at:string}
type Billing={franchise_id:string;franchise_name:string;reference_month:string;has_plan:boolean;plan_name:string;billing_model:string;rides_count:number;gross_ride_value:number;included_rides:number;overage_rides:number;monthly_fee:number;fixed_fee_per_ride:number;per_ride_amount:number;overage_fee_per_ride:number;overage_amount:number;percentage_rate:number;percentage_amount:number;adjustments_total:number;adjustments:Adjustment[];total_due:number;due_date:string;invoice_id:string|null;invoice_status:string;paid_at:string|null}
type Collection={overdue_days:number;open_overdue_amount:number;operation_suspended:boolean;allow_new_rides:boolean;allow_new_drivers:boolean;license_status:string}
type PixCharge={id:string;invoice_id:string;txid:string;qrcode:string|null;qrcode_image:string|null;visualization_link:string|null;amount:number;status:string;provider_status:string|null;expires_at:string|null;paid_at:string|null}
type CardCharge={id:string;invoice_id:string;charge_id:number;payment_url:string;amount:number;status:string;provider_status:string|null;paid_at:string|null}

const brl=(v:number)=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(v||0))
const monthLabel=(iso:string)=>new Intl.DateTimeFormat('pt-BR',{month:'long',year:'numeric'}).format(new Date(`${iso.slice(0,7)}-15T12:00:00`)).toUpperCase()
function previousMonth(value:string){const[y,m]=value.split('-').map(Number);return new Date(Date.UTC(y,m-2,1)).toISOString().slice(0,7)}
const signed=(v:number,formatter:(n:number)=>string)=>`${v>0?'+':''}${formatter(v)}`

export default function FranchiseInvoicePage(){
 const[month,setMonth]=useState(new Date().toISOString().slice(0,7)),[bill,setBill]=useState<Billing|null>(null),[previousBill,setPreviousBill]=useState<Billing|null>(null),[collection,setCollection]=useState<Collection|null>(null),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false)
 const[pix,setPix]=useState<PixCharge|null>(null),[pixBusy,setPixBusy]=useState(false),[pixMsg,setPixMsg]=useState('')
 const[card,setCard]=useState<CardCharge|null>(null),[cardBusy,setCardBusy]=useState(false),[cardMsg,setCardMsg]=useState('')

 async function checkPix(ref:string){
  const{data,error}=await supabase.functions.invoke('franchise-invoice-pix',{body:{action:'status',reference_month:ref}})
  if(error){setPixMsg(error.message);return false}
  if(data?.error){setPixMsg(String(data.error));return false}
  setPix((data?.charge||null) as PixCharge|null);return Boolean(data?.paid)
 }
 async function checkCard(ref:string){
  const{data,error}=await supabase.functions.invoke('franchise-invoice-card',{body:{action:'status',reference_month:ref}})
  if(error){setCardMsg(error.message);return false}
  if(data?.error){setCardMsg(String(data.error));return false}
  setCard((data?.charge||null) as CardCharge|null);return Boolean(data?.paid)
 }
 async function load(){
  setBusy(true);setMsg('');setPixMsg('');setCardMsg('')
  const{data:{user}}=await supabase.auth.getUser();if(!user){setMsg('Sessão não encontrada.');setBusy(false);return}
  const{data:p,error:pe}=await supabase.from('profiles').select('franchise_id').eq('id',user.id).single();const fid=String(p?.franchise_id||user.app_metadata?.franchise_id||'')
  if(pe||!fid){setMsg(pe?.message||'Franquia não vinculada.');setBusy(false);return}
  const ref=`${month}-01`,previousRef=`${previousMonth(month)}-01`
  const[b,c,pb]=await Promise.all([
   supabase.rpc('get_franchise_billing_summary',{p_franchise_id:fid,p_reference_month:ref}),
   supabase.rpc('get_franchise_collection_state',{p_franchise_id:fid}),
   supabase.rpc('get_franchise_billing_summary',{p_franchise_id:fid,p_reference_month:previousRef}),
  ])
  if(b.error||c.error){setMsg(b.error?.message||c.error?.message||'Não foi possível carregar a fatura.');setBusy(false);return}
  const current=b.data as Billing;setBill(current);setPreviousBill(pb.error?null:pb.data as Billing);setCollection(c.data as Collection);setPix(null);setCard(null)
  if(current?.invoice_id&&!current?.paid_at&&current?.invoice_status!=='paid'){
   const[pixPaid,cardPaid]=await Promise.all([checkPix(ref),checkCard(ref)])
   if(pixPaid||cardPaid){const[rb,rc]=await Promise.all([supabase.rpc('get_franchise_billing_summary',{p_franchise_id:fid,p_reference_month:ref}),supabase.rpc('get_franchise_collection_state',{p_franchise_id:fid})]);if(rb.data)setBill(rb.data as Billing);if(rc.data)setCollection(rc.data as Collection)}
  }
  setBusy(false)
 }
 useEffect(()=>{void load()},[month])

 async function createPix(){
  if(!bill)return;setPixBusy(true);setPixMsg('Gerando QR Code Pix na Efí...')
  const{data,error}=await supabase.functions.invoke('franchise-invoice-pix',{body:{action:'create',reference_month:`${month}-01`}})
  setPixBusy(false);if(error){setPixMsg(error.message);return}if(data?.error){setPixMsg(String(data.error));if(data?.charge)setPix(data.charge as PixCharge);return}
  setPix((data?.charge||null) as PixCharge|null);setPixMsg(data?.paid?'Pagamento já confirmado.':'Pix gerado. Use o QR Code ou o Copia e Cola.');if(data?.paid)void load()
 }
 async function refreshPix(){setPixBusy(true);const paidNow=await checkPix(`${month}-01`);setPixBusy(false);if(paidNow){setPixMsg('Pagamento confirmado pela Efí.');void load()}else setPixMsg('Status do Pix atualizado.')}
 async function copyPix(){if(!pix?.qrcode)return;try{await navigator.clipboard.writeText(pix.qrcode);setPixMsg('Código Pix copiado.')}catch{setPixMsg('Não foi possível copiar automaticamente. Selecione o código e copie manualmente.')}}

 async function createCard(){
  if(!bill)return
  const popup=window.open('about:blank','_blank')
  setCardBusy(true);setCardMsg('Criando checkout seguro de cartão na Efí...')
  const{data,error}=await supabase.functions.invoke('franchise-invoice-card',{body:{action:'create',reference_month:`${month}-01`}})
  setCardBusy(false)
  if(error||data?.error){if(popup)popup.close();setCardMsg(String(data?.error||error?.message||'Falha ao gerar cobrança por cartão.'));if(data?.charge)setCard(data.charge as CardCharge);return}
  const charge=(data?.charge||null) as CardCharge|null;setCard(charge);setCardMsg(data?.paid?'Pagamento já confirmado.':'Checkout de cartão criado na Efí.')
  if(data?.paid){if(popup)popup.close();void load();return}
  if(charge?.payment_url){if(popup)popup.location.href=charge.payment_url;else window.location.href=charge.payment_url}else if(popup)popup.close()
 }
 async function refreshCard(){setCardBusy(true);const paidNow=await checkCard(`${month}-01`);setCardBusy(false);if(paidNow){setCardMsg('Pagamento por cartão confirmado pela Efí.');void load()}else setCardMsg('Status do cartão atualizado.')}

 const paid=Boolean(bill?.paid_at||bill?.invoice_status==='paid'||pix?.status==='paid'||card?.status==='paid')
 const pixActive=pix?.status==='active',cardActive=card?.status==='active'
 const rows=useMemo(()=>{if(!bill||!bill.has_plan)return[];const out:{label:string;qty:string;unit:string;total:number;kind?:string}[]=[];out.push({label:`Mensalidade (Plano ${bill.plan_name})`,qty:'1',unit:brl(bill.monthly_fee),total:bill.monthly_fee});if(bill.included_rides>0)out.push({label:`Corridas incluídas (${bill.included_rides})`,qty:String(Math.min(bill.rides_count,bill.included_rides)),unit:brl(0),total:0});if(bill.overage_rides>0||bill.overage_fee_per_ride>0)out.push({label:'Corridas excedentes',qty:String(bill.overage_rides),unit:brl(bill.overage_fee_per_ride),total:bill.overage_amount});if(bill.fixed_fee_per_ride>0)out.push({label:'Taxa por corrida (Matriz)',qty:String(bill.rides_count),unit:brl(bill.fixed_fee_per_ride),total:bill.per_ride_amount});if(bill.percentage_rate>0)out.push({label:'Percentual sobre faturamento',qty:`${bill.percentage_rate}%`,unit:brl(bill.gross_ride_value),total:bill.percentage_amount});for(const a of bill.adjustments||[])out.push({label:a.description,qty:'—',unit:a.type==='fine'?'Multa':a.type==='credit'?'Crédito':a.type==='discount'?'Desconto':'Ajuste',total:Number(a.amount),kind:a.amount<0?'credit':'adjustment'});return out},[bill])
 const comparable=Boolean(bill?.has_plan&&previousBill?.has_plan)
 const comparison=useMemo(()=>{if(!bill||!previousBill||!comparable)return null;const due=Number(bill.total_due)-Number(previousBill.total_due),rides=Number(bill.rides_count)-Number(previousBill.rides_count),gross=Number(bill.gross_ride_value)-Number(previousBill.gross_ride_value);const duePct=Number(previousBill.total_due)>0?due/Number(previousBill.total_due)*100:null;return{due,rides,gross,duePct}},[bill,previousBill,comparable])

 return <div className="regional-home">
  <div className="regional-heading"><div><div className="eyebrow">Financeiro · CLICK-GO</div><h1>Fatura CLICK-GO</h1><p>Demonstrativo da franquia com pagamento por Pix QR Code ou cartão.</p></div><div style={{display:'flex',gap:8,alignItems:'end'}}><div className="field"><label>Mês</label><input className="input" type="month" value={month} onChange={e=>setMonth(e.target.value)}/></div><button className="button secondary" onClick={()=>void load()} disabled={busy}><RefreshCw size={15}/>Atualizar</button></div></div>
  {msg&&<div className="regional-alert">{msg}</div>}
  {collection?.operation_suspended&&<div style={{padding:14,border:'1px solid #d22',background:'#fff0f0',color:'#8b1111',borderRadius:12,marginBottom:16}}><strong>Sua licença está suspensa.</strong> Regularize a fatura CLICK-GO. Após confirmação do pagamento, a reativação automática seguirá a regra definida pela Matriz.</div>}
  {bill&&!bill.has_plan?<div className="card empty">Nenhum plano contratado foi encontrado para este período.</div>:bill&&<>
   <div className="card"><div className="section-heading"><div><div className="eyebrow">Fatura do mês</div><h2>{monthLabel(bill.reference_month)}</h2><p className="subtitle">Franquia {bill.franchise_name} · Plano {bill.plan_name}</p></div><span className={'pill '+(paid?'green':collection?.overdue_days?'red':'yellow')}>{paid?'Pago':collection?.overdue_days?`${collection.overdue_days} dias em atraso`:'Aguardando pagamento'}</span></div>
    <div className="table-wrap"><table className="table"><thead><tr><th>Item</th><th>Qtde/Base</th><th>Valor unitário</th><th style={{textAlign:'right'}}>Total</th></tr></thead><tbody>{rows.map((r,i)=><tr key={`${r.label}-${i}`}><td>{r.kind==='credit'?'✅ ':''}{r.label}</td><td>{r.qty}</td><td>{r.unit}</td><td style={{textAlign:'right',fontWeight:700}}>{brl(r.total)}</td></tr>)}<tr><td colSpan={3}><strong>TOTAL DEVIDO À MATRIZ</strong></td><td style={{textAlign:'right',fontSize:22,fontWeight:900}}>{brl(bill.total_due)}</td></tr></tbody></table></div>
    <div style={{display:'flex',justifyContent:'space-between',gap:16,flexWrap:'wrap',marginTop:18}}><div><small>Vencimento</small><strong style={{display:'block',fontSize:18}}>{bill.due_date?new Date(bill.due_date+'T12:00:00').toLocaleDateString('pt-BR'):'—'}</strong>{paid&&bill.paid_at&&<small>Pago em {new Date(bill.paid_at).toLocaleString('pt-BR')}</small>}</div>{!paid&&<div className="toolbar"><button className="button" onClick={()=>void createPix()} disabled={pixBusy||cardActive} title={cardActive?'Já existe cobrança por cartão ativa':'Gerar Pix QR Code'}><QrCode size={15}/>{pixBusy?'Gerando...':pixActive?'Abrir Pix':'Pix QR Code'}</button><button className="button secondary" onClick={()=>void createCard()} disabled={cardBusy||pixActive} title={pixActive?'Já existe Pix ativo':'Pagar no checkout seguro da Efí'}><CreditCard size={15}/>{cardBusy?'Gerando...':cardActive?'Abrir cartão':'Pagar com cartão'}</button></div>}</div>
    <p className="subtitle" style={{marginTop:12}}>Escolha apenas um meio por vez. O Pix é exibido no CLICK-GO; o cartão abre o checkout seguro da Efí, sem o CLICK-GO receber número ou CVV do cartão.</p>
   </div>

   <div className="section card"><div className="section-heading"><div><div className="eyebrow"><TrendingUp size={14}/> Comparação mensal</div><h3>{comparable&&previousBill?`${monthLabel(bill.reference_month)} × ${monthLabel(previousBill.reference_month)}`:'Histórico do ciclo'}</h3></div></div>{comparison&&previousBill?<><div className="regional-kpis"><div className="regional-kpi"><span>Total devido</span><strong>{signed(comparison.due,brl)}</strong><small>anterior {brl(previousBill.total_due)}{comparison.duePct===null?'':` · ${comparison.duePct>=0?'+':''}${comparison.duePct.toFixed(1)}%`}</small></div><div className="regional-kpi"><span>Corridas</span><strong>{signed(comparison.rides,n=>n.toLocaleString('pt-BR'))}</strong><small>anterior {previousBill.rides_count.toLocaleString('pt-BR')}</small></div><div className="regional-kpi"><span>Faturamento das corridas</span><strong>{signed(comparison.gross,brl)}</strong><small>anterior {brl(previousBill.gross_ride_value)}</small></div></div><p className="subtitle" style={{marginTop:10,marginBottom:0}}>A comparação é apenas informativa e não altera o valor nem cria uma cobrança.</p></>:<p className="subtitle" style={{margin:0}}>Não há um ciclo anterior contratado com base comparável para este mês. Assim que houver dois ciclos válidos, a evolução aparecerá aqui.</p>}</div>

   {pix&&!paid&&<div className="section card" style={{borderColor:'#d5bb00'}}><div className="section-heading"><div><div className="eyebrow">Pix Efí</div><h3>{brl(Number(pix.amount||bill.total_due))}</h3><p className="subtitle">Status: {pix.provider_status||pix.status} · TXID {pix.txid}</p></div><button className="button secondary" onClick={()=>void refreshPix()} disabled={pixBusy}><RefreshCw size={14}/>Atualizar status</button></div><div style={{display:'grid',gridTemplateColumns:pix.qrcode_image?'220px minmax(0,1fr)':'1fr',gap:18,alignItems:'center'}}>{pix.qrcode_image&&<img src={pix.qrcode_image} alt="QR Code Pix da fatura CLICK-GO" style={{width:220,maxWidth:'100%',background:'#fff',padding:8,border:'1px solid #ddd',borderRadius:12}}/>}<div><label style={{display:'block',fontSize:12,fontWeight:700,marginBottom:6}}>Pix Copia e Cola</label><textarea className="input" readOnly value={pix.qrcode||''} style={{minHeight:110,fontSize:11}}/><div className="toolbar" style={{marginTop:9}}><button className="button" onClick={()=>void copyPix()} disabled={!pix.qrcode}><Copy size={14}/>Copiar Pix</button>{pix.visualization_link&&<a className="button secondary" href={pix.visualization_link} target="_blank" rel="noreferrer"><ExternalLink size={14}/>Abrir na Efí</a>}</div>{pix.expires_at&&<small style={{display:'block',marginTop:8}}>Expira em {new Date(pix.expires_at).toLocaleString('pt-BR')}.</small>}</div></div>{pixMsg&&<div className="regional-alert" style={{marginTop:12,marginBottom:0}}>{pixMsg}</div>}</div>}
   {!pix&&pixMsg&&<div className="regional-alert">{pixMsg}</div>}

   {card&&!paid&&<div className="section card"><div className="section-heading"><div><div className="eyebrow">Cartão · checkout Efí</div><h3>{brl(Number(card.amount||bill.total_due))}</h3><p className="subtitle">Status: {card.provider_status||card.status} · cobrança #{card.charge_id}</p></div><button className="button secondary" onClick={()=>void refreshCard()} disabled={cardBusy}><RefreshCw size={14}/>Atualizar status</button></div><div className="toolbar"><a className="button" href={card.payment_url} target="_blank" rel="noreferrer"><CreditCard size={15}/>Abrir pagamento seguro</a></div><p className="subtitle" style={{marginTop:10}}>O preenchimento do cartão ocorre no ambiente da Efí. Ao retornar ao CLICK-GO, clique em “Atualizar status” para confirmar o pagamento.</p>{cardMsg&&<div className="regional-alert" style={{marginTop:12,marginBottom:0}}>{cardMsg}</div>}</div>}
   {!card&&cardMsg&&<div className="regional-alert">{cardMsg}</div>}

   <div className="section"><div className="regional-kpis"><div className="regional-kpi"><span>Corridas concluídas</span><strong>{bill.rides_count.toLocaleString('pt-BR')}</strong><small>somente viagens do ciclo contratado</small></div><div className="regional-kpi"><span>Incluídas no plano</span><strong>{bill.included_rides.toLocaleString('pt-BR')}</strong><small>{bill.overage_rides.toLocaleString('pt-BR')} excedentes</small></div><div className="regional-kpi"><span>Faturamento em corridas</span><strong>{brl(bill.gross_ride_value)}</strong><small>base do período</small></div><div className="regional-kpi"><span>Ajustes</span><strong>{brl(bill.adjustments_total)}</strong><small>créditos, descontos ou multas</small></div></div></div>
   <div className="section card"><div className="section-heading"><div><h3>Como esta cobrança funciona</h3><p className="subtitle">A fatura é materializada automaticamente e vence no ciclo seguinte; o Franqueado não altera as taxas definidas pela Matriz.</p></div><CalendarDays size={20}/></div><p style={{margin:0,lineHeight:1.65}}>{bill.billing_model==='hybrid'?'Neste plano híbrido, o total é formado pela mensalidade, pela taxa da Matriz aplicada a cada corrida concluída e pelo valor adicional das corridas que ultrapassam a franquia mensal.':bill.billing_model==='fixed_per_ride'?'Neste plano, o total é formado pela mensalidade mais a taxa da Matriz por corrida concluída.':bill.billing_model==='percentage'?'Neste plano, o total é formado pela mensalidade mais o percentual contratado sobre o faturamento das corridas concluídas.':'Neste plano livre, a cobrança principal é a mensalidade contratada.'}</p></div>
  </>}
 </div>
}