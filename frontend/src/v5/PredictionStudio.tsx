import {useEffect,useRef,useState} from 'react';
import {Activity,ArrowRight,CheckCircle2,Download,Pause,Play,RotateCcw,ShieldCheck,Sparkles} from 'lucide-react';
import {ModelExplanation} from '../v52/ModelExplanation';
import {DEMO,downloadText,safeCell} from '../api';
import type {Dataset} from '../types';
import {api} from '../api';
import {PredictionJourney} from '../components/animations/PredictionJourney';
import {Notice,number} from '../components/Shared';
import {platformRequest,errorText} from './client';
import {usePlatform} from './PlatformGate';
import frozen from './demoInference.json';
import './research.css';

const stages=['Protocol design','Site activation','Recruitment','Treatment','Follow-up','Study completion'];
const explanations=[
 'Inspect the protocol, evidence and feature availability before interpreting a prediction.',
 'Site preparation is part of the illustrated research journey. Site-specific timing is not estimated here.',
 'Recruitment depends on actual site capacity and eligibility. Explore explicit assumptions in Digital Twin.',
 'Treatment scheduling follows the protocol. This animation does not simulate treatment efficacy.',
 'Follow-up and data collection affect observed duration. Individual stage durations are not predicted.',
 'Review the estimate, uncertainty, model version and limitations before exporting the evidence.',
];
export function EvidenceJourney({days}:{days?:number}){
 const [step,setStep]=useState(0),[playing,setPlaying]=useState(false);
 useEffect(()=>{if(!playing)return;const t=setInterval(()=>setStep(v=>{if(v===5){setPlaying(false);return v}return v+1}),1800);return()=>clearInterval(t)},[playing]);
 return <section className="panel v5-journey"><header className="panel-heading"><h2>Understand the trial journey</h2><span className="phase">Illustration</span></header><div className="panel-padding"><div className="v5-journey-stages">{stages.map((label,i)=><button key={label} className={i===step?'current':i<step?'past':''} onClick={()=>{setStep(i);setPlaying(false)}} aria-current={i===step?'step':undefined}><span>{i<step?<CheckCircle2 size={18}/>:i+1}</span><strong>{label}</strong></button>)}</div><div className="v5-journey-story" aria-live="polite"><Activity size={27}/><div><h3>{stages[step]}</h3><p>{explanations[step]}</p></div></div><div className="v5-inline"><button className="btn secondary" onClick={()=>{if(step===5)setStep(0);setPlaying(!playing)}}>{playing?<Pause size={16}/>:<Play size={16}/>} {playing?'Pause':'Play journey'}</button><button className="btn secondary" onClick={()=>{setStep(0);setPlaying(false)}}><RotateCcw size={16}/>Reset</button>{days!==undefined&&<span>Model total: <strong>{number(days)} days</strong></span>}</div><p className="small muted">Stage positions and animation speed are illustrative. Only the total estimate above comes from the model; no stage duration or treatment effect is inferred.</p></div></section>;
}

export function PredictionStudio({dataset,autoPredict=false,onAutoDone,onNavigate,onScenario}:{dataset:Dataset;autoPredict?:boolean;onAutoDone?:()=>void;onNavigate:(path:string)=>void;onScenario?:(studyId:string,modelName:string,study?:any)=>void}){
 const {can}=usePlatform();
 const [models,setModels]=useState<any[]>([]),[batch,setBatch]=useState<any>(null),[history,setHistory]=useState<any[]>([]),[selected,setSelected]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(''),[model,setModel]=useState('active'),[mode,setMode]=useState('retrospective'),[task,setTask]=useState('duration'),[packet,setPacket]=useState<any>(null),[packetError,setPacketError]=useState('');
 const autoRun=useRef('');
 const load=async()=>{if(DEMO){setModels((frozen as any).models||[]);setBatch((frozen as any).batch||null);return}const [m,h]=await Promise.all([platformRequest<any>('/models'),platformRequest<any>(`/inference?dataset_id=${encodeURIComponent(dataset.id)}`)]);setModels(m.items);setHistory(h.items||[]);if(!autoPredict)setBatch(h.items?.[0]||null)};
 useEffect(()=>{setBatch(null);setHistory([]);setSelected(0);setError('');setPacket(null);load().catch(e=>setError(errorText(e)))},[dataset.id]);
 const predict=async()=>{if(DEMO){setError('Run the full application to predict on imported data.');return}setBusy(true);setError('');try{const result=await platformRequest<any>('/inference/batch',{method:'POST',body:JSON.stringify({dataset_id:dataset.id,model_id:model,task,limit:100,mode})},180000);setBatch(result);setSelected(0);setHistory(h=>[result,...h])}catch(e){setError(errorText(e))}finally{setBusy(false);onAutoDone?.()}};
 useEffect(()=>{if(autoPredict&&!DEMO&&autoRun.current!==dataset.id){autoRun.current=dataset.id;predict()}},[autoPredict,dataset.id]);
 const resultTask=batch?.model?.task||task;
 const items=batch?.items||[],item=items[selected],pred=item?.prediction,available=item?.status==='available'&&pred?.status==='available';
 useEffect(()=>{let alive=true;setPacket(null);setPacketError('');if(item?.nct_id&&!DEMO)api.visualizations(dataset.id,item.nct_id).then(value=>{if(alive)setPacket(value)}).catch(e=>{if(alive)setPacketError(errorText(e))});return()=>{alive=false}},[dataset.id,batch?.id,item?.nct_id]);
 const exportCsv=()=>{const columns=['nct_id','status','duration_days','raw_prolonged_probability','lower_days','upper_days','model_id','input_sha256'];const rows=items.map((r:any)=>[r.nct_id,r.status,r.prediction?.duration_days,r.prediction?.probability,r.prediction?.uncertainty?.lower_days,r.prediction?.uncertainty?.upper_days,batch.model?.id,batch.dataset?.sha256]);downloadText([columns,...rows].map(r=>r.map(safeCell).join(',')).join('\n'),'cti-predictions.csv','text/csv')};
 const hasInterval=pred?.uncertainty?.status==='available'&&typeof pred.uncertainty.lower_days==='number'&&Number.isFinite(pred.uncertainty.lower_days)&&typeof pred.uncertainty.upper_days==='number'&&Number.isFinite(pred.uncertainty.upper_days);
 return <div className="cti-prediction-studio">
  {DEMO&&<Notice>Frozen prediction evidence · run the full application for new predictions.</Notice>}{error&&<Notice kind="error">{error}</Notice>}
  <section className="panel"><div className="v5-prediction-controls">
   <label>Objective<select value={task} onChange={e=>{setTask(e.target.value);setModel('active');setBatch(DEMO?(frozen as any).batches?.[e.target.value]||null:null);setSelected(0)}}><option value="duration">Duration & prolonged-duration probability</option><option value="phase">Phase consistency</option></select></label>
   <label>Saved model<select value={model} onChange={e=>setModel(e.target.value)}><option value="active">Active approved model</option>{models.filter(m=>m.task===task&&m.status==='approved').map(m=><option key={m.id} value={m.id}>{m.name}</option>)}</select></label>
   <label>Evidence mode<select value={mode} onChange={e=>setMode(e.target.value)}><option value="retrospective">Retrospective research</option><option value="pretrial">Strict pretrial</option></select></label>
   <button className="btn primary" disabled={busy||!can('predict')} onClick={predict}>{busy?<span className="spinner"/>:<Sparkles size={17}/>} {busy?'Predicting…':'Predict now'}</button>
  </div><details className="cti-prediction-method"><summary>Prediction scope</summary><p>Uses an approved saved model on up to 100 records. Strict pretrial mode checks supplied feature timestamps. Training does not run during prediction.</p></details></section>
  {busy&&<div className="v5-inference-busy" role="status"><span className="v5-signal"/><strong>Applying the saved model</strong></div>}
  {batch?<><div className="v5-result-heading"><div><h2>Prediction results</h2><p>{items.length} records · {batch.model?.name||batch.model?.id}</p></div><div className="v5-inline">
   {history.length>1&&<select aria-label="Saved prediction run" value={batch.id||''} onChange={e=>{const saved=history.find(r=>r.id===e.target.value);if(saved){setBatch(saved);setSelected(0)}}}>{history.map(r=><option value={r.id} key={r.id}>{new Date(r.created_at).toLocaleString()}</option>)}</select>}
   <button className="btn secondary" onClick={exportCsv}><Download size={16}/>CSV</button><button className="btn secondary" onClick={()=>downloadText(JSON.stringify(batch,null,2),'cti-prediction-evidence.json','application/json')}>Evidence</button><button className="btn secondary" onClick={()=>window.print()}>PDF</button>
  </div></div>
  <div className="v5-prediction-layout"><section className="panel"><header className="panel-heading"><h2>Studies</h2><span>{batch.summary?.available??0} available</span></header><div className="v5-record-list">{items.map((r:any,i:number)=><button key={r.nct_id} className={selected===i?'active':''} onClick={()=>setSelected(i)}><div><strong>{r.nct_id}</strong><small>{r.status}</small></div><span>{typeof r.prediction?.duration_days==='number'?`${number(r.prediction.duration_days)} days`:r.prediction?.predicted_phase||'—'}</span></button>)}</div></section>
  <section className="panel v5-prediction-detail"><div className="panel-padding"><h3>{item?.nct_id}</h3>{available?<>
   <div className="v5-result-values">{typeof pred.duration_days==='number'?<><div><small>Total duration</small><strong>{number(pred.duration_days)}<em> days</em></strong></div><div><small>Prolonged-duration probability</small><strong>{number(pred.probability*100)}<em>%</em></strong></div></>:<div><small>Predicted phase</small><strong>{pred.predicted_phase}</strong></div>}</div>
   {pred.uncertainty&&<div className="v5-interval"><strong>Duration prediction interval</strong><p>{hasInterval?`${number(pred.uncertainty.lower_days)}–${number(pred.uncertainty.upper_days)} days`:'Unavailable or unbounded'}</p></div>}
   {typeof pred.prolonged_threshold_days==='number'&&<p className="small muted">Prolonged: above {number(pred.prolonged_threshold_days)} days.</p>}
   <ModelExplanation key={item.nct_id} evidence={pred.duration_explanation||pred.explanation}/>
   {resultTask==='duration'&&<div className="v5-inline"><button className="btn secondary" disabled={!can('run_scenarios')} onClick={()=>onScenario?.(item.nct_id,pred.model_name||batch.model?.branch||'recommended',packet?.workspace?.study)}>Compare a scenario<ArrowRight size={16}/></button></div>}
   <details><summary>Evidence & limitations</summary><p>{pred.prediction_scope}</p><p>Attributions describe the fitted model; they do not establish causality. Interval coverage can change with time or population shift.</p>{(item.availability_warnings||[]).map((w:string)=><p key={w}>{w}</p>)}<pre className="code-display">{JSON.stringify({explanation:pred.duration_explanation||pred.explanation,extrapolation:pred.extrapolation,calibration:pred.calibration},null,2)}</pre></details>
   </>:<Notice>{item?.reason||pred?.reason||(item?.status==='blocked'?'Pretrial evidence checks blocked this record.':'Prediction unavailable.')}</Notice>}
   <details><summary>Input & model provenance</summary><pre className="code-display">{JSON.stringify({dataset:batch.dataset,model:batch.model,created_at:batch.created_at,mode:batch.mode},null,2)}</pre></details>
  </div></section></div>
  {packet?.workspace?.study&&available&&<PredictionJourney key={`${batch.id}-${item.nct_id}`} study={packet.workspace.study} duration={resultTask==='duration'?pred:packet.workspace.duration} phase={resultTask==='phase'?pred:packet.workspace.phase} provenance={{...packet.workspace.provenance,prediction_run_id:batch.id,model:batch.model}}/>}
  {packetError&&<Notice kind="error">{packetError}</Notice>}
  <details className="cti-prediction-method"><summary>Run warnings</summary>{(batch.warnings||[]).map((w:string)=><p key={w}>{w}</p>)}</details>
  </>:!busy&&<section className="panel v5-empty-evidence"><Activity size={34}/><h2>Ready to predict</h2><button className="btn secondary" onClick={()=>onNavigate('data')}>Choose data</button></section>}
 </div>;
}

export function ModelRegistry(){
 const {project}=usePlatform();const [data,setData]=useState<any>({items:[]}),[error,setError]=useState(''),[busy,setBusy]=useState(''),[notes,setNotes]=useState('');
 const load=()=>DEMO?Promise.resolve(setData({items:(frozen as any).models||[]})):platformRequest<any>('/models').then(setData);
 useEffect(()=>{load().catch(e=>setError(errorText(e)))},[project.id]);
 const act=async(id:string,action:string)=>{setBusy(id);setError('');try{await platformRequest(`/models/${encodeURIComponent(id)}/${action}`,{method:'POST',body:JSON.stringify(action==='approve'?{notes,research_only_acknowledged:true}:{notes})});await load();window.dispatchEvent(new Event('cti-models-changed'))}catch(e){setError(errorText(e))}finally{setBusy('')}};
 return <><Notice>Approval here permits research screening only. It does not establish clinical validation. Training produces a candidate; it never silently replaces the active model.</Notice>{error&&<Notice kind="error">{error}</Notice>}{project.role==='owner'&&<section className="panel"><div className="panel-padding"><label>Approval / activation rationale<textarea value={notes} onChange={e=>setNotes(e.target.value)} placeholder="Record the evaluation you reviewed and the intended research use." rows={3}/></label></div></section>}<div className="v5-model-grid">{data.items.map((m:any)=><section className="panel" key={m.id}><header className="panel-heading"><h2>{m.name}</h2><span className={`phase ${m.active?'green':''}`}>{m.active?'Active':m.status}</span></header><div className="panel-padding"><p>{m.task} · {m.branch||m.id}</p><p>Approval scope: <strong>{m.approval_scope||'not approved'}</strong></p>{m.test_metrics&&<div className="cti-model-metrics">{m.task==='duration'?<><span>MAE <strong>{number(m.test_metrics.regression?.mae)} days</strong></span><span>RMSE <strong>{number(m.test_metrics.regression?.rmse)} days</strong></span><span>Brier <strong>{typeof m.test_metrics.classification?.brier==='number'?m.test_metrics.classification.brier.toFixed(4):'—'}</strong></span></>:<><span>Accuracy <strong>{typeof m.test_metrics.accuracy==='number'?(m.test_metrics.accuracy*100).toFixed(1)+'%':'—'}</strong></span><span>Macro F1 <strong>{typeof m.test_metrics.macro_f1==='number'?m.test_metrics.macro_f1.toFixed(3):'—'}</strong></span></>}</div>}{m.status==='approved'&&!DEMO&&<button className="btn secondary" onClick={()=>api.modelAnalysis(m.task,m.id).catch(e=>setError(errorText(e)))}>Download analysis</button>}<details><summary>Evaluation evidence and limits</summary>{(m.warnings||[]).map((w:string)=><p className="small muted" key={w}>{w}</p>)}<pre className="code-display">{JSON.stringify(m,null,2)}</pre></details>{project.role==='owner'&&!DEMO&&<div className="v5-inline">{m.status==='candidate'&&<button className="btn secondary" disabled={!!busy||notes.trim().length<10} onClick={()=>act(m.id,'approve')}>Approve for research</button>}{m.status==='approved'&&!m.active&&<button className="btn primary" disabled={!!busy||notes.trim().length<10} onClick={()=>act(m.id,'activate')}>Activate / roll back</button>}</div>}</div></section>)}</div>{!data.items.length&&<Notice>No model entries are registered. The owner can install the release artifacts or train and approve a candidate.</Notice>}</>;
}
