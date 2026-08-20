export default function Page(){return <>
<div className="topbar"><div><div className="eyebrow">Atendimento</div><h1 className="title">Chamados de suporte</h1><p className="subtitle">Centralize chamados de franqueados, motoristas e passageiros com prioridade, responsável e histórico.</p></div><button className="button">+ Novo chamado</button></div>
<div className="grid-3"><div className="card"><div className="label">Abertos</div><div className="metric">0</div></div><div className="card"><div className="label">Em andamento</div><div className="metric">0</div></div><div className="card"><div className="label">Urgentes</div><div className="metric kpi-bad">0</div></div></div>
<div className="section"><div className="table-wrap"><table className="table"><thead><tr><th>Chamado</th><th>Solicitante</th><th>Franquia</th><th>Prioridade</th><th>Status</th><th>Responsável</th></tr></thead><tbody><tr><td colSpan={6} className="empty">Nenhum chamado aberto.</td></tr></tbody></table></div></div>
</>}
