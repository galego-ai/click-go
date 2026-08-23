'use client'

import AppAdvertisingBanner from '@/components/AppAdvertisingBanner'

export default function PassengerLayout({children}:{children:React.ReactNode}){
  return <div style={{minHeight:'100vh',background:'#f4f4f6'}}>
    <AppAdvertisingBanner audience="passenger"/>
    {children}
  </div>
}
