import {useEffect,useState, type ReactNode} from 'react';
import {Pause,Play,RefreshCw,Info} from 'lucide-react';
import {DEMO,researchRequest} from '../../api';
import type {Study} from '../../types';
import './animations.css';

export interface AnimationStudyProps {datasetId:string;nctId?:string;study?:Study;rows?:Study[];active?:boolean;modelName?:string}
export interface StudyVisualization {
 workspace:any;
 timeline:{status:string;dates:{field:string;label:string;value:string|null;precision:string|null;date_type:string|null;availability:string}[];observed_duration_days:number|null;predicted_duration_days:number|null;predicted_completion_date:string|null;stage_durations:null;reason:string};
 recruitment:{status:string;stages:{stage:string;count:number|null;source_field:string|null;availability:string;reporting_rows:number}[];sites:number|null;site_source_field:string|null;target_enrollment:number|null;total_enrolled:number|null;total_studies:number};
 fusion:{status:string;model_name:string|null;input_mode:string|null;family:string|null;method:string|null;branches:{id:string;label:string;encoder:string;fields:string[]}[];components:{model_name:string;weight:number;prediction:number}[];reason:string|null};
 explanation:any;provenance:any;
}
export function useStudyEvidence({datasetId,nctId,active=true,modelName='recommended'}:AnimationStudyProps) {
 const [state,setState]=useState<{key:string;data:StudyVisualization|null;loading:boolean;error:string}>({key:'',data:null,loading:false,error:''});
 const [revision,setRevision]=useState(0);
 const key=`${datasetId}/${nctId || ''}/${modelName}`;
 useEffect(()=>{
  let cancelled=false;
  if(!active||!datasetId||!nctId){setState({key,data:null,loading:false,error:''});return}
  if(DEMO){setState({key,data:null,loading:false,error:'Live study evidence requires the connected research workspace.'});return}
  setState({key,data:null,loading:true,error:''});
  researchRequest<StudyVisualization>(`/visualizations/study?dataset_id=${encodeURIComponent(datasetId)}&nct_id=${encodeURIComponent(nctId)}&model_name=${encodeURIComponent(modelName)}`).then(data=>{if(!cancelled)setState({key,data,loading:false,error:''})}).catch(e=>{if(!cancelled)setState({key,data:null,loading:false,error:e instanceof Error?e.message:'Study evidence could not be loaded.'})});
  return()=>{cancelled=true};
 },[datasetId,nctId,active,modelName,revision]);
 const visible=state.key===key?state:{key,data:null,loading:!!nctId,error:''};
 return {data:visible.data,loading:visible.loading,error:visible.error,retry:()=>setRevision(v=>v+1)};
}
export function useMotion(active=true) {
 const prefersReduced=()=>typeof window!=='undefined'&&(document.documentElement.dataset.ctiMotion==='reduced'||window.matchMedia('(prefers-reduced-motion: reduce)').matches);
 const [reduced,setReduced]=useState(prefersReduced);
 const [paused,setPaused]=useState(false);
 useEffect(()=>{const query=window.matchMedia('(prefers-reduced-motion: reduce)');const change=()=>setReduced(prefersReduced());query.addEventListener('change',change);window.addEventListener('cti-preferences-changed',change);return()=>{query.removeEventListener('change',change);window.removeEventListener('cti-preferences-changed',change)}},[]);
 return {running:active&&!paused&&!reduced,paused,reduced,toggle:()=>setPaused(v=>!v)};
}
export function MotionControl({motion}:{motion:ReturnType<typeof useMotion>}) {
 return <button type="button" className="cti-motion-button" onClick={motion.toggle} disabled={motion.reduced} aria-pressed={motion.paused}>{motion.running?<Pause size={15}/>:<Play size={15}/>} {motion.reduced?'Reduced motion':motion.paused?'Resume motion':'Pause motion'}</button>;
}
export function AnimationPanel({title,description,children,motion,eyebrow='EVIDENCE EXPLORER'}:{title:string;description:string;children:ReactNode;motion?:ReturnType<typeof useMotion>;eyebrow?:string}) {
 return <section className={`cti-animation${motion&&!motion.running?' cti-motion-paused':''}`}><header className="cti-animation-header"><div><h2>{title}</h2><p>{description}</p></div>{motion&&<MotionControl motion={motion}/>}</header><div className="cti-animation-body">{children}</div></section>;
}
export function EvidenceState({nctId,loading,error,retry}:{nctId?:string;loading:boolean;error:string;retry:()=>void}) {
 if(error)return <div className="cti-evidence-state cti-evidence-error" role="alert"><Info size={20}/><div><strong>Evidence unavailable</strong><p>{error}</p><button className="cti-motion-button" type="button" onClick={retry}><RefreshCw size={15}/>Retry</button></div></div>;
 return <div className="cti-evidence-state" role="status"><Info size={20}/><div><strong>{loading?'Loading selected-study evidence…':nctId?'No evidence returned':'Select a study to inspect its evidence'}</strong><p>{loading?'Waiting for the research API.':'Choose an imported study using the selector above.'}</p></div></div>;
}
export function Provenance({data}:{data:any}) {
 if(!data)return null;
 return <details className="cti-animation-details"><summary>Source and model provenance</summary><pre>{JSON.stringify(data,null,2)}</pre></details>;
}
