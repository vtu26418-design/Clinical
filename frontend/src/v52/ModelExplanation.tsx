import {useState} from 'react';
import {Play} from 'lucide-react';

type Explanation={method?:string;scope?:string;units?:string;note?:string;features?:{feature:string;contribution?:number;importance?:number}[];components?:{model_name:string;weight:number;prediction:number}[]};
export function ModelExplanation({evidence}:{evidence:Explanation|undefined}){
 const [replay,setReplay]=useState(0);
 if(!evidence)return <p className="v52-caption">This output has no feature-attribution evidence.</p>;
 const features=(evidence.features||[]).map(f=>({name:f.feature,value:f.contribution??f.importance})).filter((f):f is {name:string;value:number}=>typeof f.value==='number'&&Number.isFinite(f.value));
 const scale=Math.max(...features.map(f=>Math.abs(f.value)),1e-12);
 return <section className="v52-explanation"><header><div><h3>Model explanation</h3><p>{evidence.method} · {evidence.scope||'scope unspecified'}</p></div>{features.length>0&&<button className="icon-btn" aria-label="Replay feature evidence animation" onClick={()=>setReplay(v=>v+1)}><Play size={17}/></button>}</header>
 {features.length>0?<div className="v52-attributions" key={replay} role="img" aria-label={`Model evidence in ${evidence.units||'model units'}. Values are listed for each feature.`}>{features.map((f,i)=><div key={f.name}><span title={f.name}>{f.name}</span><div><i className={f.value<0?'negative':''} style={{width:`${Math.abs(f.value)/scale*100}%`,animationDelay:`${i*45}ms`}}/></div><strong>{f.value.toLocaleString(undefined,{maximumFractionDigits:4})}</strong></div>)}</div>:<p className="v52-caption">No feature-specific attribution is available for this model output.</p>}
 {evidence.components&&<table><caption>Actual fusion component outputs · {evidence.units}</caption><thead><tr><th>Model branch</th><th>Weight</th><th>Prediction</th></tr></thead><tbody>{evidence.components.map(c=><tr key={c.model_name}><td>{c.model_name}</td><td>{c.weight}</td><td>{c.prediction.toLocaleString(undefined,{maximumFractionDigits:3})}</td></tr>)}</tbody></table>}
 <p className="v52-caption">Units: {evidence.units||'not specified'}. {evidence.note}</p></section>;
}
