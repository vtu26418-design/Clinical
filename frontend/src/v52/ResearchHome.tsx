import {useEffect,useRef,useState} from 'react';
import {ArrowRight,BarChart3,BookOpen,Check,ChevronRight,Database,FileText,GitBranch,Layers,Pause,Play,ShieldCheck} from 'lucide-react';
import {DEMO} from '../api';
import type {Dataset} from '../types';
import {MolecularAnimation} from '../components/animations/MolecularAnimation';
import {useMotion} from '../components/animations/shared';
import {ScenePanel} from '../components/three/ScenePanel';
import {educationPlayback,RESEARCH_JOURNEY} from '../components/education/education';
import '../components/education/education.css';

const steps=[['Import & validate','Bring in trial records and run quality checks.','data'],['Apply saved models','Use approved models for your research question.','predict'],['Explore scenarios','Adjust assumptions and compare model outputs.','digital-twin'],['Review evidence','Trace predictions to records and source documents.','protocols']];

export function MolecularScene(){
 const [angle,setAngle]=useState(0),motion=useMotion();
 return <div className={`v52-molecule ${motion.reduced?'cti-education-still':''}`} onPointerMove={e=>{if(motion.reduced)return;setAngle((e.clientX-e.currentTarget.getBoundingClientRect().left)/e.currentTarget.clientWidth*12-6)}} onPointerLeave={()=>setAngle(0)}>
  <svg viewBox="0 0 600 290" role="img" aria-label="Decorative molecular helix; not a biological simulation" style={{transform:`perspective(800px) rotateY(${motion.reduced?0:angle}deg)`}}>
   <defs><linearGradient id="helix-tone" x2="1" y2="1"><stop stopColor="#27bec7"/><stop offset="1" stopColor="#134b78"/></linearGradient></defs>
   <g className="v52-helix">
    {Array.from({length:44},(_,i)=>{const x=30+i*12.5,y=145+Math.sin(i*.25)*66,y2=145-Math.sin(i*.25)*66;return <g key={i}><line x1={x} x2={x} y1={y} y2={y2} stroke="#7bbdcf" strokeWidth="1" opacity=".6"/><circle cx={x} cy={y} r={3.4+Math.cos(i*.25)} fill="#0b4265"/><circle cx={x} cy={y2} r={3.4-Math.cos(i*.25)} fill="#10aebe"/></g>})}
    {[0,Math.PI].map((phase,j)=><path key={j} d={Array.from({length:220},(_,i)=>`${i?'L':'M'}${30+i*2.46},${145+Math.sin(i*.05+phase)*66}`).join(' ')} fill="none" stroke="url(#helix-tone)" strokeWidth="1.5"/>)}</g>
   {[35,100,180,270,370,440,520,565].map((x,i)=><g key={x} opacity=".5"><circle cx={x} cy={40+(i%3)*90} r={i%2?4:2} fill="#32b8c8"/><path d={`M${x} ${40+(i%3)*90} l35 22 26 -38`} fill="none" stroke="#b6d9e5"/></g>)}
  </svg><div><strong>Evidence at every step</strong><span>Inspect the source. Understand the uncertainty.</span></div>
 </div>;
}

export function ModelPipeline(){
 const [playing,setPlaying]=useState(false),[step,setStep]=useState(0),motion=useMotion();
 const panel=useRef<HTMLElement>(null),[panelVisible,setPanelVisible]=useState(true),[tabVisible,setTabVisible]=useState(()=>typeof document==='undefined'||document.visibilityState!=='hidden');
 useEffect(()=>{const change=()=>setTabVisible(document.visibilityState!=='hidden');document.addEventListener('visibilitychange',change);return()=>document.removeEventListener('visibilitychange',change)},[]);
 useEffect(()=>{if(!panel.current||typeof IntersectionObserver==='undefined')return;const observer=new IntersectionObserver(([entry])=>setPanelVisible(entry.isIntersecting),{threshold:0.05});observer.observe(panel.current);return()=>observer.disconnect()},[]);
 useEffect(()=>{if(!motion.running)setPlaying(false)},[motion.running]);
 useEffect(()=>{if(!playing||!motion.running||!panelVisible||!tabVisible)return;const id=setInterval(()=>setStep(s=>(s+1)%4),1700);return()=>clearInterval(id)},[playing,motion.running,panelVisible,tabVisible]);
 const stages=[{icon:FileText,title:'Trial metadata + protocol text',text:'Structured and text inputs'},{icon:Layers,title:'Feature preparation',text:'Selected model representations'},{icon:Database,title:'Saved model',text:'Approved duration or phase artifact'},{icon:BarChart3,title:'Prediction + uncertainty',text:'Versioned research evidence'}];
 return <section className="v52-surface v52-pipeline" ref={panel}><header><div><h2>A transparent model pipeline</h2><p>From trial data to predictions, with traceability at every step.</p></div><button className="icon-btn" disabled={motion.reduced} title={motion.reduced?'Reduced motion is on; choose a stage below':undefined} aria-label={playing?'Pause pipeline animation':'Play pipeline animation'} onClick={()=>setPlaying(v=>!v)}>{playing?<Pause size={18}/>:<Play size={18}/>}</button></header><div className={`v52-pipeline-track ${playing&&motion.running&&panelVisible&&tabVisible?'playing':''}`}>{stages.map(({icon:Icon,title,text},i)=><button key={title} className={step===i?'current':''} onClick={()=>{setStep(i);setPlaying(false)}} aria-pressed={step===i}><Icon size={23}/><strong>{title}</strong><small>{text}</small>{i<3&&<ArrowRight className="v52-pipeline-arrow" size={17}/>}</button>)}</div><p className="v52-caption">Illustrative workflow · predictions use approved artifacts. Modalities depend on the selected model; the default duration baseline does not consume text.</p></section>;
}

export function ResearchHome({dataset,onNavigate}:{dataset:Dataset;onNavigate:(route:string)=>void}){
 const motion=useMotion(),[journeyStep,setJourneyStep]=useState(0),[journeyPlaying,setJourneyPlaying]=useState(false),[journeySpeed,setJourneySpeed]=useState(1),[helix3D,setHelix3D]=useState(true);
 useEffect(()=>{if(!motion.running)setJourneyPlaying(false)},[motion.running]);
 const current=RESEARCH_JOURNEY[journeyStep];
 const journeyFallback=<div className="cti-research-journey-flat" role="group" aria-label="Research workflow, 2D view"><ol>{RESEARCH_JOURNEY.map((item,index)=><li key={item.title} aria-current={journeyStep===index?'step':undefined}><button type="button" onClick={()=>{setJourneyStep(index);setJourneyPlaying(false)}}><span>{index+1}</span><strong>{item.title}</strong></button></li>)}</ol><p>{current.detail}</p></div>;
 const links=[{title:'Predict trial duration',text:'Saved models, uncertainty and explanations',icon:BarChart3,route:'predict'},{title:'Find source evidence',text:'Trial records, literature and drug labels',icon:BookOpen,route:'sources'},{title:'Compare a scenario',text:'Protocol changes and explicit assumptions',icon:GitBranch,route:'digital-twin'}];
 return <div className="v52-home cti-home-v5204">
 <section className="cti-home-hero" aria-label="Clinical research introduction"><MolecularAnimation interactive height={340} scene3D={helix3D}/><div className="cti-home-helix-choice"><span className="small muted">{dataset.row_count.toLocaleString()} {dataset.is_fixture?'fixture':'imported'} records selected</span><button className="btn secondary" aria-pressed={helix3D} onClick={()=>{setHelix3D(value=>!value);setJourneyPlaying(false)}}>{helix3D?'Explore the virtual clinic':'Show DNA introduction'}</button></div></section>
 <section className="cti-home-actions" aria-label="Research actions">{links.map(({title,text,icon:Icon,route})=><button key={route} onClick={()=>onNavigate(route)}><Icon size={23}/><div><strong>{title}</strong><span>{text}</span></div><ArrowRight size={17}/></button>)}</section>
 <section className="cti-research-journey" aria-label="Walk through the research journey">{helix3D?<div className="v52-surface cti-research-journey-paused"><h2>Walk through the research journey</h2>{journeyFallback}</div>:<ScenePanel kind="journey" title="Walk through the research journey" subtitle="Import, review, predict, explain and compare." mode="conceptual" steps={RESEARCH_JOURNEY.map(({title,detail})=>({title,detail}))} labels={RESEARCH_JOURNEY.map(item=>item.title)} values={[]} step={journeyStep} onStepChange={setJourneyStep} playing={educationPlayback(journeyPlaying,motion)} onPlayingChange={setJourneyPlaying} speed={journeySpeed} onSpeedChange={setJourneySpeed} fallback={journeyFallback}/>}<div className="cti-research-journey-action"><span>Step {journeyStep+1} of {RESEARCH_JOURNEY.length} · {current.title}</span><button className="btn primary" onClick={()=>onNavigate(current.route)}>{current.action}<ArrowRight size={16}/></button></div></section>
 </div>;
}
