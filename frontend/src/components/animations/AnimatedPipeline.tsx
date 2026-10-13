import {GuidedEvidence} from './EvidenceGuide';
import {pipelineScene} from './guidedEvidence';
import {useEffect,useState} from 'react';
import {FileText,Settings2,Network,ChartNoAxesCombined,RefreshCw,CheckCircle2,Clock} from 'lucide-react';
import {DEMO,researchRequest} from '../../api';
import {durationEvidence,formatNumber} from './evidence';
import {AnimationPanel,EvidenceState,Provenance,useMotion,useStudyEvidence,type AnimationStudyProps} from './shared';

export function PipelineDiagram({loading=false,hasStudy=false,hasResult=false,modelName}:{loading?:boolean;hasStudy?:boolean;hasResult?:boolean;modelName?:string}) {
 const nodes=[{label:'Protocol',text:hasStudy?'Selected source record':'Awaiting selection',icon:FileText},{label:'Processing',text:hasResult?'Saved inference returned':loading?'Request in progress':'Saved model preprocessing',icon:Settings2},{label:'Model',text:modelName||'Compatible saved model',icon:Network},{label:'Result',text:hasResult?'Prediction returned':loading?'Waiting for API':'Output unavailable',icon:ChartNoAxesCombined}];
 return <ol className={`cti-pipeline${loading?' cti-pipeline-running':''}`} aria-label="Saved-model evidence flow">{nodes.map((node,i)=><li key={node.label}><div className={`cti-pipeline-node${i===0&&hasStudy||i===3&&hasResult?' is-recorded':''}`}><node.icon size={24}/></div><strong>{node.label}</strong><small>{node.text}</small>{i<nodes.length-1&&<span className="cti-pipeline-link" aria-hidden="true"><i/><i/><i/></span>}</li>)}</ol>;
}
export function AnimatedPipeline(props:AnimationStudyProps) {
 const evidence=useStudyEvidence(props),motion=useMotion(props.active);
 const [job,setJob]=useState<any>(null),[jobError,setJobError]=useState(''),[revision,setRevision]=useState(0);
 useEffect(()=>{
  let cancelled=false,timer:ReturnType<typeof setTimeout>;
  setJob(null);setJobError('');
  if(!props.datasetId||!props.nctId||props.active===false||DEMO)return;
  const load=()=>researchRequest<any>(`/pipeline-status?dataset_id=${encodeURIComponent(props.datasetId)}`).then(result=>{if(cancelled)return;setJob(result);if(['queued','running'].includes(result.status))timer=setTimeout(load,5000)}).catch(e=>{if(!cancelled)setJobError(e instanceof Error?e.message:'Experiment status is unavailable.')});
  load();return()=>{cancelled=true;clearTimeout(timer)};
 },[props.datasetId,props.nctId,props.active,revision]);
 const duration=evidence.data?.workspace.duration,prediction=durationEvidence(duration);
 return <AnimationPanel title="From protocol to prediction" description="Follow the real request and inspect the saved-model experiment lifecycle." motion={motion} guided={!!evidence.data}>{!evidence.data?<>{evidence.loading&&<PipelineDiagram loading={motion.running} hasStudy={!!props.study}/>}<EvidenceState nctId={props.nctId} {...evidence}/></>:<><GuidedEvidence {...pipelineScene(duration,job)} active={props.active} playing={motion.running} onPlayingChange={motion.setPlaying}/><PipelineDiagram hasStudy hasResult={prediction.available} loading={evidence.loading&&motion.running} modelName={duration?.model_name}/><div className="cti-evidence-metrics"><div><span>Selected study</span><strong>{evidence.data.workspace.study.nct_id}</strong></div><div><span>Model total duration</span><strong>{prediction.available?`${formatNumber(prediction.days)} days`:'Unavailable'}</strong></div><div><span>Prediction status</span><strong>{duration?.status||'Unknown'}</strong></div></div>{!prediction.available&&<p className="cti-animation-note">{prediction.reason}</p>}<Provenance data={evidence.data.provenance}/></>}{props.nctId&&<section className="cti-animation-subsection"><div className="cti-animation-subheading"><h3>Training experiment lifecycle</h3><button type="button" className="cti-motion-button" onClick={()=>setRevision(v=>v+1)}><RefreshCw size={14}/>Refresh status</button></div>{jobError?<p role="alert" className="cti-animation-error">{jobError}</p>:job?<><p className="cti-animation-note"><strong>{job.current_step}</strong> · {job.status} · {job.active_experiments_count} active / {job.total_experiments_count} recorded experiments</p><div className="cti-job-stages">{(job.pipeline_steps||[]).map((s:any)=><div key={s.name} className={`cti-job-stage ${s.status}`}><span>{s.status==='complete'?<CheckCircle2 size={17}/>:<Clock size={17}/>}</span><strong>{s.name}</strong><small>{s.status}</small></div>)}</div>{['queued','running'].includes(job.status)&&<div className={`cti-request-line${motion.running?' is-running':''}`} aria-hidden="true"><i/></div>}{job.experiment&&<Provenance data={job.experiment}/>}</>:<p role="status" className="cti-animation-note">Loading actual experiment state…</p>}<p className="cti-animation-note">Movement means a request or recorded experiment is active. Elapsed time does not imply a completion percentage.</p></section>}</AnimationPanel>;
}
