import {Canvas} from '@react-three/fiber';
import type {ScenePanelProps} from './types';
import {ScientificWorld} from '../../v5205/science/ScientificWorld';
import {defaultSettings} from '../../v5205/science/templates';
import type {ScienceScene,ScienceFocus} from '../../v5205/science/types';
import '../../v5205/science/science.css';
interface CanvasProps extends ScenePanelProps {step:number;running:boolean;speed:number;quality:'low'|'standard';reduced:boolean;onFailure:()=>void}
/** Analytical pages show processing. DNA is reserved for the explicitly conceptual helix. */
export function analyticalScene(kind:ScenePanelProps['kind']):ScienceScene{return kind==='helix'?'dna':'pipeline'}
export default function SceneCanvas(props:CanvasProps){
 const scene=props.scientificScene??analyticalScene(props.kind),focus:ScienceFocus=props.step===0?'input':props.step===props.steps.length-1?'output':'processing';
 const labels=scene==='pipeline'?[props.steps[0]?.title||'Source',props.steps[Math.floor(props.steps.length/2)]?.title||'Processing',props.steps.at(-1)?.title||'Output']:[];
 return <div className="cti-scene-canvas" style={{background:'#071320'}} aria-hidden="true"><Canvas orthographic camera={{position:[0,0,15],zoom:50,near:0.1,far:60}} frameloop={props.running?'always':'demand'} dpr={props.quality==='low'?1:[1,1.5]} gl={{antialias:props.quality!=='low',powerPreference:'low-power'}}><ScientificWorld scene={scene} focus={focus} settings={{...defaultSettings,detail:props.quality,speed:props.speed===0.5||props.speed===1.5||props.speed===2?props.speed:1}} running={props.running} reduced={props.reduced} onFailure={props.onFailure} labels={labels}/></Canvas><div className="cti-scene-canvas-note" style={{color:'#c2d3e1',background:'#071320d9',padding:'6px 8px',borderRadius:5}}>{scene==='dna'?'Conceptual DNA · no genomic inputs':`Illustrative ${scene==='pipeline'?'processing flow':scene} · ${props.steps[props.step]?.title||'source evidence below'}`}{!props.reduced&&<span>Actual values in evidence details</span>}</div></div>
}
