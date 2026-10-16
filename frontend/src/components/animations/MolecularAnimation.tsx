import {useEffect,useState,type PointerEvent} from 'react';
import {RotateCcw} from 'lucide-react';
import {AnimationPanel,useMotion,type AnimationStudyProps} from './shared';
import {ScenePanel} from '../three/ScenePanel';
import {educationPlayback} from '../education/education';
import '../education/education.css';

export interface MolecularAnimationProps extends Partial<AnimationStudyProps> {interactive?:boolean;height?:number;className?:string;scene3D?:boolean}
const HELIX_STEPS = [
 {title:'Clinical Trial Intelligence',detail:'Welcome to the Clinical Trial Intelligence Workbench, an explainable multimodal AI platform for protocol complexity analysis and prolonged duration risk prediction.'},
 {title:'Explore the evidence',detail:'Review protocol complexity, apply approved saved models, and inspect their predictions and explanations. The helix is decorative; no genomic inputs are used.'},
];
export function MolecularAnimation({active=true,interactive=true,height=260,className,scene3D=true}:MolecularAnimationProps) {
 const motion=useMotion(active),[rotation,setRotation]=useState(0),[tilt,setTilt]=useState(0);
 const [step,setStep]=useState(0),[playing,setPlaying]=useState(false),[speed,setSpeed]=useState(1);
 useEffect(()=>{if(!motion.running){setPlaying(false);setTilt(0)}},[motion.running]);
 const move=(event:PointerEvent<HTMLDivElement>)=>{if(!interactive||motion.reduced||!active||event.pointerType==='touch')return;const bounds=event.currentTarget.getBoundingClientRect();if(!bounds.width||!bounds.height)return;setTilt((event.clientY-bounds.top)/bounds.height-.5);setRotation((event.clientX-bounds.left)/bounds.width*Math.PI*2)};
 const rungs=Array.from({length:32},(_,i)=>{
  const angle=i*.38+rotation,y=22+i*6.8;
  const strand=(side:number)=>{const x=Math.sin(angle+side*Math.PI)*64,z=Math.cos(angle+side*Math.PI);return {x:180+x+tilt*(y-130)*.22,y:y+x*tilt*.16,z}};
  return {a:strand(0),b:strand(1),i};
 });
 const paths=[0,1].map(side=>rungs.map((r,i)=>`${i?'L':'M'}${side?r.b.x:r.a.x},${side?r.b.y:r.a.y}`).join(' '));
 const fallback=<div className="cti-helix-layout"><div className="cti-helix-canvas" style={{height}} onPointerMove={move} onPointerLeave={()=>setTilt(0)}><svg style={{height,maxHeight:height}} viewBox="0 0 360 260" role="img" aria-label="Decorative helix; no genomic inputs or biological simulation"><path d={paths[0]} fill="none" stroke="#17776d" strokeWidth="2" opacity=".5"/><path d={paths[1]} fill="none" stroke="#647a78" strokeWidth="2" opacity=".4"/>{rungs.map(r=><g key={r.i}><line x1={r.a.x} y1={r.a.y} x2={r.b.x} y2={r.b.y} stroke="#a6c9c1" strokeWidth="2.5" opacity=".8"/>{[r.a,r.b].sort((a,b)=>a.z-b.z).map((p,i)=><circle key={i} cx={p.x} cy={p.y} r={4+(p.z+1)*1.7} fill={p===r.a?'#17776d':'#647a78'} opacity={.45+(p.z+1)*.25}/>)}</g>)}</svg></div><div className="cti-helix-copy"><span className="cti-evidence-badge">Decorative · no genomic inputs</span><h3>Clinical research, explained.</h3><p>Explore source records, inspect model provenance, and compare explicit scenarios in this workspace.</p>{interactive&&<><label className="cti-helix-rotation">Helix rotation<input type="range" min="0" max="360" step="1" value={Math.round(rotation*180/Math.PI)} onChange={e=>setRotation(Number(e.target.value)*Math.PI/180)} aria-valuetext={`${Math.round(rotation*180/Math.PI)} degrees`}/></label><button type="button" className="cti-motion-button" onClick={()=>{setRotation(0);setTilt(0)}}><RotateCcw size={15}/>Reset orientation</button></>}{motion.reduced&&<p className="cti-helix-motion-note">Reduced motion is on. The rotation control changes the static view.</p>}</div></div>;
 return <div className={className}>{scene3D?<ScenePanel kind="helix" title="Explainable Multimodal AI for Clinical Trial Intelligence" subtitle="Protocol Complexity and Prolonged Duration Risk Prediction" mode="conceptual" steps={HELIX_STEPS} values={[]} active={active} step={step} onStepChange={setStep} playing={educationPlayback(playing,motion)} onPlayingChange={setPlaying} speed={speed} onSpeedChange={setSpeed} fallback={fallback}/>:<AnimationPanel title="Explainable Multimodal AI for Clinical Trial Intelligence" description="A decorative helix. Adjust rotation to explore its form." eyebrow="RESEARCH WORKSPACE">{fallback}</AnimationPanel>}</div>;
}
