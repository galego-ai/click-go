'use client'

import ManagementNotificationComposer from '@/components/ManagementNotificationComposer'

export default function FranchiseNotificationsPage(){
  return <div className="regional-home">
    <div className="regional-heading"><div><div style={{fontSize:11,fontWeight:900,letterSpacing:'.08em',textTransform:'uppercase',color:'#9a7d00'}}>Comunicação</div><h1>Notificações</h1><p>Envie avisos para motoristas e passageiros da sua própria operação.</p></div></div>
    <ManagementNotificationComposer context="franchise"/>
  </div>
}
