'use client'

import {FormEvent,useEffect,useState} from 'react'
import {supabase} from '@/lib/supabase'

type Method={id:string;method_type:string;provider:string|null;brand:string|null;last4:string|null;is_default:boolean;active:boolean}
type Config={configured:boolean;account_identifier:string|null;environment:'production'|'sandbox'}
const box:React.CSSProperties={background:'#141414',border:'1px solid #292929',borderRadius:16,padding:18}
const input:React.CSSProperties={width:'100%',background:'#0d0d0d',color:'#fff',border:'1px solid #333',borderRadius:10,padding:'11px 12px',boxSizing:'border-box'}
const btn:React.CSSProperties={background:'#ffd400',color:'#000',border:0,borderRadius:10,padding:'11px 14px',fontWeight:800,cursor:'pointer'}

export default function PassengerPaymentMethods({passengerId,methods,onChanged}:{passengerId:string;methods:Method[];onChanged:()=>Promise<void>|void}){
 const[config,setConfig]=useState<Config|null>(null),[msg,setMsg]=useState(''),[busy,setBusy]=useState(false),[showCard,setShowCard]=useState(false)
 useEffect(()=>{void loadConfig()},[])
 async function loadConfig(){const{data,error}=await supabase.functions.invoke('efi-card',{body:{action:'config'}});if(error||data?.error){setMsg(data?.error||error?.message||'Não foi possível consultar a configuração Efí.');return}setConfig(data as Config)}
 async function addBasic(type:'cash'|'pix'){
  setBusy(true);setMsg('')
  try{
   if(methods.some(m=>m.method_type===type&&m.active))throw new Error(type==='pix'?'PIX já está cadastrado.':'Dinheiro já está cadastrado.')
   if(methods.length)await supabase.from('passenger_payment_methods').update({is_default:false}).eq('passenger_id',passengerId)
   const{error}=await supabase.from('passenger_payment_methods').insert({passenger_id:passengerId,method_type:type,provider:type==='pix'?'efi':null,is_default:true,active:true});if(error)throw error
   setMsg(type==='pix'?'PIX adicionado. O QR Code será gerado pela Efí quando você solicitar uma corrida com PIX.':'Dinheiro adicionado.');await onChanged()
  }catch(e:any){setMsg(e.message||'Erro ao adicionar forma de pagamento.')}finally{setBusy(false)}
 }
 async function saveCard(e:FormEvent<HTMLFormElement>){
  e.preventDefault();setBusy(true);setMsg('Tokenizando cartão diretamente com a Efí...')
  try{
   let cfg=config;if(!cfg){await loadConfig();const{data,error}=await supabase.functions.invoke('efi-card',{body:{action:'config'}});if(error||data?.error)throw new Error(data?.error||error?.message);cfg=data as Config}
   if(!cfg?.configured||!cfg.account_identifier)throw new Error('Falta configurar o Identificador de conta da Efí para habilitar cartões.')
   const f=new FormData(e.currentTarget);const brand=String(f.get('brand')||'visa');const number=String(f.get('number')||'').replace(/\D/g,'');const cvv=String(f.get('cvv')||'').replace(/\D/g,'');const expirationMonth=String(f.get('expiration_month')||'').padStart(2,'0');const expirationYear=String(f.get('expiration_year')||'');const holderName=String(f.get('holder_name')||'').trim();const holderDocument=String(f.get('holder_document')||'').replace(/\D/g,'')
   if(number.length<13||cvv.length<3||expirationMonth.length!==2||expirationYear.length!==4||!holderName||holderDocument.length!==11)throw new Error('Confira número, CVV, validade, nome e CPF do titular.')
   const mod=await import('payment-token-efi');const EfiPay:any=(mod as any).default||mod
   const tokenized=await EfiPay.CreditCard.setAccount(cfg.account_identifier).setEnvironment(cfg.environment).setCreditCardData({brand,number,cvv,expirationMonth,expirationYear,holderName,holderDocument,reuse:true}).getPaymentToken()
   if(!tokenized?.payment_token||!tokenized?.card_mask)throw new Error('A Efí não retornou o token do cartão.')
   const{data,error}=await supabase.functions.invoke('efi-card',{body:{action:'save_method',payment_token:tokenized.payment_token,card_mask:tokenized.card_mask,brand}});if(error||data?.error)throw new Error(data?.error||error?.message||'Erro ao salvar cartão tokenizado.')
   e.currentTarget.reset();setShowCard(false);setMsg('Cartão cadastrado com segurança. O CLICK-GO guarda apenas o token Efí e os 4 últimos dígitos.');await onChanged()
  }catch(e:any){setMsg(e?.error_description||e?.message||'Não foi possível cadastrar o cartão na Efí.')}finally{setBusy(false)}
 }
 async function setDefault(id:string){setBusy(true);await supabase.from('passenger_payment_methods').update({is_default:false}).eq('passenger_id',passengerId);const{error}=await supabase.from('passenger_payment_methods').update({is_default:true}).eq('id',id).eq('passenger_id',passengerId);setMsg(error?error.message:'Forma principal atualizada.');if(!error)await onChanged();setBusy(false)}
 async function remove(m:Method){setBusy(true);setMsg('');if(m.method_type==='card'){const{data,error}=await supabase.functions.invoke('efi-card',{body:{action:'delete_method',method_id:m.id}});if(error||data?.error){setMsg(data?.error||error?.message||'Erro ao remover cartão.');setBusy(false);return}}else{const{error}=await supabase.from('passenger_payment_methods').update({active:false,is_default:false}).eq('id',m.id).eq('passenger_id',passengerId);if(error){setMsg(error.message);setBusy(false);return}}setMsg('Forma de pagamento removida.');await onChanged();setBusy(false)}
 const label=(m:Method)=>m.method_type==='cash'?'Dinheiro':m.method_type==='pix'?'PIX Efí':`${String(m.brand||'Cartão').toUpperCase()} •••• ${m.last4||''}`
 return <div style={{display:'grid',gap:14}}>
  <div><h2>Formas de pagamento</h2><p className="subtitle">PIX e cartão integrados à Efí Bank. O número completo do cartão e o CVV não são armazenados pelo CLICK-GO.</p></div>
  <div style={{display:'flex',gap:9,flexWrap:'wrap'}}><button style={{...btn,background:'#222',color:'#fff'}} disabled={busy} onClick={()=>void addBasic('cash')}>+ Dinheiro</button><button style={{...btn,background:'#222',color:'#fff'}} disabled={busy} onClick={()=>void addBasic('pix')}>+ PIX Efí</button><button style={btn} disabled={busy} onClick={()=>setShowCard(v=>!v)}>💳 Cadastrar cartão</button></div>
  {showCard&&<form onSubmit={saveCard} style={{...box,display:'grid',gap:10,borderColor:'#665600'}}><h3 style={{margin:0}}>Cadastrar cartão com Efí Bank</h3><div style={{color:'#9ca3af',fontSize:13}}>A tokenização acontece diretamente pela biblioteca oficial da Efí. Use um cartão de crédito habilitado pela sua conta Efí.</div>{config&&!config.configured&&<div style={{background:'#3b1d0d',padding:10,borderRadius:10,color:'#fed7aa'}}>Integração de cartão aguardando o <b>Identificador de conta Efí</b>.</div>}<div style={{display:'grid',gridTemplateColumns:'160px 1fr',gap:10}}><select name="brand" required style={input}><option value="visa">Visa</option><option value="mastercard">Mastercard</option><option value="elo">Elo</option><option value="amex">American Express</option></select><input name="number" required inputMode="numeric" autoComplete="cc-number" placeholder="Número do cartão" style={input}/></div><div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:10}}><input name="expiration_month" required inputMode="numeric" maxLength={2} autoComplete="cc-exp-month" placeholder="Mês (MM)" style={input}/><input name="expiration_year" required inputMode="numeric" maxLength={4} autoComplete="cc-exp-year" placeholder="Ano (AAAA)" style={input}/><input name="cvv" required inputMode="numeric" maxLength={4} autoComplete="cc-csc" placeholder="CVV" style={input}/></div><input name="holder_name" required autoComplete="cc-name" placeholder="Nome do titular como no cartão" style={input}/><input name="holder_document" required inputMode="numeric" placeholder="CPF do titular" style={input}/><button style={btn} disabled={busy}>{busy?'Processando...':'Tokenizar e salvar cartão'}</button></form>}
  <div style={{display:'grid',gap:9}}>{methods.map(m=><div key={m.id} style={{...box,display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'}}><div><b>{label(m)}</b><div style={{fontSize:12,color:'#9ca3af'}}>{m.is_default?'Forma principal':m.method_type==='card'?'Token Efí salvo com segurança':''}</div></div><div style={{display:'flex',gap:7}}>{!m.is_default&&<button style={{...btn,background:'#222',color:'#fff'}} disabled={busy} onClick={()=>void setDefault(m.id)}>Definir principal</button>}<button style={{...btn,background:'#3a1b1b',color:'#fff'}} disabled={busy} onClick={()=>void remove(m)}>Remover</button></div></div>)}{!methods.length&&<div style={box}>Nenhuma forma de pagamento cadastrada.</div>}</div>
  {msg&&<div style={{...box,borderColor:'#665600',color:'#ffe66b'}}>{msg}</div>}
 </div>
}
