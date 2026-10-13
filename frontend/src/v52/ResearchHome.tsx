import {useEffect,useState} from 'react';
import {ArrowRight,BarChart3,BookOpen,Check,ChevronRight,Database,FileText,GitBranch,Layers,Pause,Play,ShieldCheck} from 'lucide-react';
import {DEMO} from '../api';
import type {Dataset} from '../types';
import {MolecularAnimation} from '../components/animations';

const steps=[['Import & validate','Bring in trial records and run quality checks.','data'],['Apply saved models','Use approved models for your research question.','predict'],['Explore scenarios','Adjust assumptions and compare model outputs.','digital-twin'],['Review evidence','Trace predictions to records and source documents.','protocols']];

export function MolecularScene(){
 const [angle,setAngle]=useState(0);
 return <div className="v52-molecule" onPointerMove={e=>setAngle((e.clientX-e.currentTarget.getBoundingClientRect().left)/e.currentTarget.clientWidth*12-6)} onPointerLeave={()=>setAngle(0)}>
  <svg viewBox="0 0 600 290" role="img" aria-label="Decorative molecular helix; not a biological simulation" style={{transform:`perspective(800px) rotateY(${angle}deg)`}}>
   <defs><linearGradient id="helix-tone" x2="1" y2="1"><stop stopColor="#27bec7"/><stop offset="1" stopColor="#134b78"/></linearGradient></defs>
   <g className="v52-helix">
    {Array.from({length:44},(_,i)=>{const x=30+i*12.5,y=145+Math.sin(i*.25)*66,y2=145-Math.sin(i*.25)*66;return <g key={i}><line x1={x} x2={x} y1={y} y2={y2} stroke="#7bbdcf" strokeWidth="1" opacity=".6"/><circle cx={x} cy={y} r={3.4+Math.cos(i*.25)} fill="#0b4265"/><circle cx={x} cy={y2} r={3.4-Math.cos(i*.25)} fill="#10aebe"/></g>})}
    {[0,Math.PI].map((phase,j)=><path key={j} d={Array.from({length:220},(_,i)=>`${i?'L':'M'}${30+i*2.46},${145+Math.sin(i*.05+phase)*66}`).join(' ')} fill="none" stroke="url(#helix-tone)" strokeWidth="1.5"/>)}</g>
   {[35,100,180,270,370,440,520,565].map((x,i)=><g key={x} opacity=".5"><circle cx={x} cy={40+(i%3)*90} r={i%2?4:2} fill="#32b8c8"/><path d={`M${x} ${40+(i%3)*90} l35 22 26 -38`} fill="none" stroke="#b6d9e5"/></g>)}
  </svg><div><strong>Evidence at every step</strong><span>Inspect the source. Understand the uncertainty.</span></div>
 </div>;
}

export function ModelPipeline(){
 const [playing,setPlaying]=useState(false),[step,setStep]=useState(0);
 useEffect(()=>{if(!playing)return;const id=setInterval(()=>setStep(s=>(s+1)%4),1700);return()=>clearInterval(id)},[playing]);
 const stages=[{icon:FileText,title:'Trial metadata + protocol text',text:'Structured and text inputs'},{icon:Layers,title:'Feature preparation',text:'Selected model representations'},{icon:Database,title:'Saved model',text:'Approved duration or phase artifact'},{icon:BarChart3,title:'Prediction + uncertainty',text:'Versioned research evidence'}];
 return <section className="v52-surface v52-pipeline"><header><div><h2>A transparent model pipeline</h2><p>From trial data to predictions, with traceability at every step.</p></div><button className="icon-btn" aria-label={playing?'Pause pipeline animation':'Play pipeline animation'} onClick={()=>setPlaying(v=>!v)}>{playing?<Pause size={18}/>:<Play size={18}/>}</button></header><div className={`v52-pipeline-track ${playing?'playing':''}`}>{stages.map(({icon:Icon,title,text},i)=><button key={title} className={step===i?'current':''} onClick={()=>{setStep(i);setPlaying(false)}} aria-pressed={step===i}><Icon size={23}/><strong>{title}</strong><small>{text}</small>{i<3&&<ArrowRight className="v52-pipeline-arrow" size={17}/>}</button>)}</div><p className="v52-caption">Illustrative workflow · predictions use approved artifacts. Modalities depend on the selected model; the default duration baseline does not consume text.</p></section>;
}

export function ResearchHome({dataset,onNavigate}:{dataset:Dataset;onNavigate:(route:string)=>void}){
 const links=[{title:'Predict trial duration',text:'Apply a saved model, then inspect uncertainty and provenance.',icon:BarChart3,route:'predict'},{title:'Find source evidence',text:'Search trial records, PubMed literature and drug labels.',icon:BookOpen,route:'sources'},{title:'Compare a scenario',text:'Explore protocol changes while preserving the original record.',icon:GitBranch,route:'digital-twin'}];
 return <div className="v52-home"><div className="v52-workflow">{steps.map(([title,text,route],i)=><button key={title} onClick={()=>onNavigate(route)}><span>{String(i+1).padStart(2,'0')}</span><div><strong>{title}</strong><p>{text}</p></div>{i<3&&<ChevronRight size={19}/>}</button>)}</div>
 <div className="v52-home-main"><section className="v52-surface v52-questions"><h2>Your next research question</h2><p>Start with a common analysis or draft your own.</p>{links.map(({title,text,icon:Icon,route})=><button key={route} onClick={()=>onNavigate(route)}><span><Icon size={24}/></span><div><strong>{title}</strong><p>{text}</p></div><ChevronRight size={18}/></button>)}</section><section className="cti-home-molecule" aria-label="Interactive decorative helix"><MolecularAnimation interactive height={300}/><p>Decorative helix · explore with your pointer.</p></section></div>
 <div className="v52-home-bottom"><ModelPipeline/><section className="v52-surface v52-readiness"><h2>Research readiness</h2><p>A clear view of the current workspace.</p><button onClick={()=>onNavigate('data')}><Database size={21}/><div><strong>{DEMO?'Offline interface preview':'Local research workspace'}</strong><small>{dataset.row_count.toLocaleString()} {dataset.is_fixture?'software fixture':'imported'} records selected</small></div><ChevronRight size={16}/></button><button onClick={()=>onNavigate('models')}><ShieldCheck size={21}/><div><strong>Saved duration + phase models</strong><small>Inspect the approved artifact and its limitations.</small></div><ChevronRight size={16}/></button><button onClick={()=>onNavigate('sources')}><Check size={21}/><div><strong>Source-linked evidence</strong><small>{DEMO?'Live search requires the full application.':'Search results retain source links and retrieval time.'}</small></div><ChevronRight size={16}/></button></section></div>
 </div>;
}
