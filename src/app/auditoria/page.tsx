import AuditManager from '@/components/AuditManager'

export default function Page(){
 return <><div className="topbar"><div><div className="eyebrow">Matriz · Governança</div><h1 className="title">Auditoria Geral</h1><p className="subtitle">Rastreie alterações críticas da rede com usuário, franquia, justificativa e valores antes/depois.</p></div></div><AuditManager/></>
}
