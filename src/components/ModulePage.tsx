type Item={n:number;title:string;description:string}
export default function ModulePage({eyebrow,title,subtitle,items,actions}:{eyebrow:string;title:string;subtitle:string;items:Item[];actions?:string[]}){
 return <>
  <div className="topbar"><div><div className="eyebrow">{eyebrow}</div><h1 className="title">{title}</h1><p className="subtitle">{subtitle}</p></div>{actions&&<div className="toolbar">{actions.map(a=><button key={a} className="button">{a}</button>)}</div>}</div>
  <div className="module-list">{items.map(i=><div className="module-item" key={i.n}><div className="module-number">{i.n}</div><div><strong>{i.title}</strong><p>{i.description}</p></div></div>)}</div>
 </>
}
