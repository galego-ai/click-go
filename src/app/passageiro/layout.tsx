'use client'

import AppAdvertisingBanner from '@/components/AppAdvertisingBanner'

export default function PassengerLayout({children}:{children:React.ReactNode}){
  return <div style={{minHeight:'100vh',background:'#080808'}}>
    <AppAdvertisingBanner audience="passenger"/>
    {children}
  </div>
}
