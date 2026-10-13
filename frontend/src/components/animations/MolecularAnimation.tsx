import {useEffect,useRef,useState,type PointerEvent} from 'react';
import {RotateCcw} from 'lucide-react';
import {AnimationPanel,useMotion,type AnimationStudyProps} from './shared';

export interface MolecularAnimationProps extends Partial<AnimationStudyProps> {interactive?:boolean;height?:number;className?:string}
export function MolecularAnimation({active=true,interactive=true,height=260,className}:MolecularAnimationProps) {
 const motion=useMotion(active),[rotation,setRotation]=useState(0),[tilt,setTilt]=useState(0),previous=useRef(0);
 useEffect(()=>{
  if(!motion.running)return;
  let frame:number;
  const animate=(time:number)=>{if(time-previous.current>32){setRotation(v=>(v+0.007)%(Math.PI*2));previous.current=time}frame=requestAnimationFrame(animate)};
  frame=requestAnimationFrame(animate);return()=>cancelAnimationFrame(frame);
 },[motion.running]);
 const move=(event:PointerEvent<HTMLDivElement>)=>{if(!interactive||!motion.running||event.pointerType==='touch')return;const bounds=event.currentTarget.getBoundingClientRect();setTilt((event.clientY-bounds.top)/bounds.height-.5);setRotation((event.clientX-bounds.left)/bounds.width*Math.PI*2)};
 const rungs=Array.from({length:32},(_,i)=>{
  const angle=i*.38+rotation,y=22+i*6.8;
  const strand=(side:number)=>{const x=Math.sin(angle+side*Math.PI)*64,z=Math.cos(angle+side*Math.PI);return {x:180+x+tilt*(y-130)*.22,y:y+x*tilt*.16,z}};
  return {a:strand(0),b:strand(1),i};
 });
 const paths=[0,1].map(side=>rungs.map((r,i)=>`${i?'L':'M'}${side?r.b.x:r.a.x},${side?r.b.y:r.a.y}`).join(' '));
 return <div className={className}><AnimationPanel title="A closer look at research" description="A decorative DNA helix. Move the pointer or adjust rotation to explore its form." motion={motion} eyebrow="RESEARCH WORKSPACE"><div className="cti-helix-layout"><div className="cti-helix-canvas" style={{height}} onPointerMove={move} onPointerLeave={()=>setTilt(0)}><svg style={{height,maxHeight:height}} viewBox="0 0 360 260" aria-hidden="true"><path d={paths[0]} fill="none" stroke="#087f8c" strokeWidth="2" opacity=".5"/><path d={paths[1]} fill="none" stroke="#10283f" strokeWidth="2" opacity=".4"/>{rungs.map(r=><g key={r.i}><line x1={r.a.x} y1={r.a.y} x2={r.b.x} y2={r.b.y} stroke="#91cad0" strokeWidth="2.5" opacity=".8"/>{[r.a,r.b].sort((a,b)=>a.z-b.z).map((p,i)=><circle key={i} cx={p.x} cy={p.y} r={4+(p.z+1)*1.7} fill={p===r.a?'#087f8c':'#10283f'} opacity={.45+(p.z+1)*.25}/>)}</g>)}</svg></div><div className="cti-helix-copy"><span className="cti-evidence-badge">Decorative · no genomic inputs</span><h3>Study evidence guides the work.</h3><p>Explore source records, inspect model provenance, and compare explicit scenarios in this workspace.</p><label className="cti-helix-rotation">Helix rotation<input type="range" min="0" max="360" step="1" value={Math.round(rotation*180/Math.PI)} onChange={e=>setRotation(Number(e.target.value)*Math.PI/180)} aria-valuetext={`${Math.round(rotation*180/Math.PI)} degrees`}/></label><button type="button" className="cti-motion-button" onClick={()=>{setRotation(0);setTilt(0)}}><RotateCcw size={15}/>Reset orientation</button></div></div></AnimationPanel></div>;
}
