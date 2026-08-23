'use client'

import {useEffect} from 'react'

const BTN_ATTR='data-clickgo-password-eye'
const INPUT_ATTR='data-clickgo-password-input'

export default function PasswordEyes(){
 useEffect(()=>{
  const buttons:HTMLButtonElement[]=[]
  function enhance(input:HTMLInputElement){
   if(input.getAttribute(INPUT_ATTR)==='1')return
   const parent=input.parentElement
   if(!parent)return
   const existing=parent.querySelector('button[aria-label*="senha" i]') as HTMLButtonElement|null
   if(existing){input.setAttribute(INPUT_ATTR,'1');return}

   input.setAttribute(INPUT_ATTR,'1')
   input.style.paddingRight='48px'
   const button=document.createElement('button')
   button.type='button'
   button.setAttribute(BTN_ATTR,'1')
   button.setAttribute('aria-label','Mostrar senha')
   button.title='Mostrar senha'
   button.textContent='👁'
   Object.assign(button.style,{
    width:'40px',height:'40px',border:'1px solid #444',borderRadius:'10px',background:'#181818',color:'#fff',cursor:'pointer',fontSize:'17px',lineHeight:'1',display:'inline-flex',alignItems:'center',justifyContent:'center',marginLeft:'8px',verticalAlign:'middle'
   } as CSSStyleDeclaration)
   button.addEventListener('click',()=>{
    const visible=input.type==='text'
    input.type=visible?'password':'text'
    button.textContent=visible?'👁':'🙈'
    button.setAttribute('aria-label',visible?'Mostrar senha':'Ocultar senha')
    button.title=visible?'Mostrar senha':'Ocultar senha'
    input.focus()
    try{input.setSelectionRange(input.value.length,input.value.length)}catch{}
   })
   input.insertAdjacentElement('afterend',button)
   buttons.push(button)
  }
  function scan(){document.querySelectorAll<HTMLInputElement>('input[type="password"]').forEach(enhance)}
  scan()
  const observer=new MutationObserver(scan)
  observer.observe(document.body,{childList:true,subtree:true})
  return()=>{observer.disconnect();buttons.forEach(b=>b.remove())}
 },[])
 return null
}
