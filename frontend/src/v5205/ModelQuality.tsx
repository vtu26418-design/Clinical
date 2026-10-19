import {useCallback,useEffect,useRef,useState} from 'react';
import {BarChart3,Download,RefreshCw,ShieldCheck} from 'lucide-react';
import {DEMO,downloadText,researchRequest} from '../api';
import './model-quality.css';

type Task='duration'|'phase';
type Values=Record<string,unknown>;
type Classification=Values&{labels:(string|number)[];confusion_matrix:number[][];per_class:({label:string|number;support:number;precision?:number|null;recall?:number|null;f1?:number|null})[];undefined_reasons?:string[]};
export type QualityRow={model_name:string;split:string;split_role:string;n:number;regression?:Values;classification:Partial<Classification>;calibrated_classification?:Partial<Classification>};
type QualityChart={kind:string;title:string;x_label:string;y_label:string;points:[number,number][];population_n:number;model_name:string;split:string};
export type QualityReport={task:Task;model:{id:string;name?:string;branch:string;artifact_version?:string;run_id?:string;manifest_sha256:string;artifact_sha256:string;selection?:unknown};selected_split:string;selected:QualityRow;baseline:QualityRow|null;charts:QualityChart[];provenance:Values;provenance_scope:string;cohort:Values;split_counts:Record<string,{n:number;role:string;prediction_rows:number}>;integrity:{artifact_and_manifest:string;evaluation_files:string;evaluation_bound_to_approval:boolean;estimator_deserialized:boolean;hashes:Record<string,string>};endpoint:{meaning:string;probability_semantics:string;prolonged_threshold_days?:number};uncertainty:{metric_confidence_intervals:{status:string;reason:string;recorded?:Values};prediction_intervals:Values};warnings:string[];chart_sampling:string};

const numeric=(value:unknown):value is number=>typeof value==='number'&&Number.isFinite(value);
function display(value:unknown,digits=3){return numeric(value)?value.toLocaleString(undefined,{maximumFractionDigits:digits}):'Unavailable'}
function text(value:unknown){return value==null?'Unavailable':typeof value==='object'?JSON.stringify(value):String(value)}
const qualityPath=(task:Task,split:string,format='json')=>`/model-quality?${new URLSearchParams({task,split,model_id:'active',format})}`;
export function fetchModelQuality(task:Task,split:string):Promise<QualityReport>{
 return DEMO?Promise.reject(Error('Model quality inspection requires the full application and its saved model evidence.')):researchRequest<QualityReport>(qualityPath(task,split));
}
async function downloadQuality(task:Task,split:string,format:'html'|'csv'){
 const headers=new Headers(),project=sessionStorage.getItem('cti-project-id'),token=sessionStorage.getItem('cti-api-token');
 if(project)headers.set('X-Project-ID',project);if(token)headers.set('Authorization',`Bearer ${token}`);
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),60000);
 try{
  const response=await fetch(`${import.meta.env.VITE_API_BASE_URL||'/api/v1'}${qualityPath(task,split,format)}`,{headers,credentials:'include',signal:controller.signal});
  if(!response.ok){if(response.status===401)window.dispatchEvent(new Event('cti-session-expired'));const body=await response.json().catch(()=>({detail:'Quality report is unavailable.'}));throw Error(typeof body.detail==='string'?body.detail:'Quality report is unavailable.')}
  downloadText(await response.text(),`${task}-${split}-model-quality.${format}`,format==='html'?'text/html':'text/csv');
 }finally{clearTimeout(timeout)}
}

type Metric={name:string;key:string;family:'regression'|'classification';unit?:string;hint:string};
const durationMetrics:Metric[]=[
 {name:'MAE',key:'mae_days',family:'regression',unit:'days',hint:'Mean absolute duration error · lower is better'},
 {name:'RMSE',key:'rmse_days',family:'regression',unit:'days',hint:'Large errors receive more weight · lower is better'},
 {name:'Median absolute error',key:'median_absolute_error_days',family:'regression',unit:'days',hint:'Middle absolute error · lower is better'},
 {name:'R²',key:'r2',family:'regression',hint:'Can be negative; undefined for constant outcomes'},
 {name:'AUROC',key:'auroc',family:'classification',hint:'Raw prolonged-risk discrimination · requires both outcomes'},
 {name:'Average precision',key:'average_precision',family:'classification',hint:'Assess alongside positive class support'},
 {name:'Brier score',key:'brier',family:'classification',hint:'Raw probability squared error · lower is better'},
 {name:'Log loss',key:'log_loss',family:'classification',hint:'Raw probability loss · lower is better'},
];
const phaseMetrics:Metric[]=[
 {name:'Phase accuracy',key:'accuracy',family:'classification',hint:'Fraction matching the recorded phase label'},
 {name:'Balanced accuracy',key:'balanced_accuracy',family:'classification',hint:'Mean recall across supported actual classes'},
 {name:'Macro F1',key:'macro_f1',family:'classification',hint:'Unweighted F1 across observed/predicted labels'},
 {name:'Log loss',key:'log_loss',family:'classification',hint:'Loss on the actual phase label · lower is better'},
 {name:'Multiclass Brier',key:'multiclass_brier',family:'classification',hint:'Sum of squared class probability errors · lower is better'},
];

export function QualityMetrics({task,row}:{task:Task;row:QualityRow}){
 return <div className="mq-metrics">{(task==='duration'?durationMetrics:phaseMetrics).map(metric=><article key={metric.key} className="mq-metric"><span>{metric.name}</span><strong>{display(row[metric.family]?.[metric.key])}{metric.unit&&numeric(row[metric.family]?.[metric.key])?<small> {metric.unit}</small>:null}</strong><p>{metric.hint}</p></article>)}</div>;
}

export function QualityConfusion({classification,title='Confusion matrix'}:{classification:Partial<Classification>;title?:string}){
 const labels=classification.labels||[],matrix=classification.confusion_matrix||[];
 if(!labels.length||!matrix.length)return null;
 const maximum=Math.max(1,...matrix.flat());
 return <article className="mq-chart mq-confusion"><h3>{title}</h3><p>Actual rows · predicted columns · counts</p><div className="table-wrap"><table><thead><tr><th scope="col">Actual / predicted</th>{labels.map(label=><th scope="col" key={label}>{label}</th>)}<th scope="col">Support</th></tr></thead><tbody>{labels.map((label,i)=><tr key={label}><th scope="row">{label}</th>{labels.map((predicted,j)=><td key={predicted} className={i===j?'mq-correct':''} style={{backgroundColor:`rgba(32,132,143,${.04+.3*(matrix[i]?.[j]||0)/maximum})`}}>{matrix[i]?.[j]??0}</td>)}<td>{matrix[i]?.reduce((total,n)=>total+n,0)??0}</td></tr>)}</tbody></table></div>{classification.undefined_reasons?.map(reason=><p className="mq-note" key={reason}>{reason}</p>)}</article>;
}

function QualityPlot({chart}:{chart:QualityChart}){
 const points=chart.points.filter(point=>point.every(numeric));
 if(!points.length)return null;
 const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
 let xmin=0,xmax=1,ymin=0,ymax=1;
 if(chart.kind==='scatter')xmax=ymax=Math.max(1,...xs,...ys)*1.04;
 else if(chart.kind!=='reliability'){xmin=Math.min(0,...xs);xmax=Math.max(1,...xs)*1.04;ymin=Math.min(0,...ys);ymax=Math.max(0,...ys);const pad=Math.max(1,(ymax-ymin)*.08);ymin-=pad;ymax+=pad}
 const x=(v:number)=>70+420*(v-xmin)/(xmax-xmin),y=(v:number)=>245-205*(v-ymin)/(ymax-ymin);
 const title=`${chart.title}. ${points.length} plotted points; ${chart.population_n.toLocaleString()} rows used for metrics.`;
 return <figure className="mq-chart"><figcaption><h3>{chart.title}</h3></figcaption><svg viewBox="0 0 540 315" role="img" aria-label={title}><title>{title}</title>{[0,.25,.5,.75,1].map(t=><g key={t}><path className="mq-grid" d={`M70 ${245-t*205}H490 M${70+t*420} 40V245`}/><text x={62} y={249-t*205} textAnchor="end">{display(ymin+t*(ymax-ymin),1)}</text><text x={70+t*420} y={264} textAnchor="middle">{display(xmin+t*(xmax-xmin),1)}</text></g>)}<path className="mq-axis" d="M70 40V245H490"/>{chart.kind==='scatter'||chart.kind==='reliability'?<path className="mq-reference" d="M70 245L490 40"/>:<path className="mq-reference" d={`M70 ${y(0)}H490`}/>}{chart.kind==='reliability'&&<polyline className="mq-reliability" points={points.map(p=>`${x(p[0])},${y(p[1])}`).join(' ')}/>}<g className="mq-points">{points.map(([left,top],i)=><circle key={i} cx={x(left).toFixed(2)} cy={y(top).toFixed(2)} r={chart.kind==='reliability'?4:2.6}><title>{`${chart.x_label}: ${display(left)}; ${chart.y_label}: ${display(top)}`}</title></circle>)}</g><text x="280" y="298" textAnchor="middle">{chart.x_label}</text><text transform="translate(15 143) rotate(-90)" textAnchor="middle">{chart.y_label}</text></svg><p>{chart.kind==='reliability'?'Occupied probability bins; dashed line is perfect reliability.':`${points.length.toLocaleString()} deterministic points shown; all ${chart.population_n.toLocaleString()} rows contribute to metrics.`}</p></figure>;
}

function QualityBaseline({report}:{report:QualityReport}){
 const baseline=report.baseline;
 if(!baseline)return <p className="mq-note">No simple baseline prediction rows are available for this approved artifact.</p>;
 const same=baseline.model_name===report.selected.model_name;
 return <section className="mq-comparison"><header><h3>Simple baseline comparison</h3><p>{same?'The active branch is the simple baseline.':`Selected ${report.selected.model_name} versus ${baseline.model_name}; identical ${report.selected.split} trials and outcomes.`}</p></header><div className="table-wrap"><table><thead><tr><th>Metric</th><th>Selected branch · n={report.selected.n.toLocaleString()}</th><th>{baseline.model_name} · n={baseline.n.toLocaleString()}</th></tr></thead><tbody>{(report.task==='duration'?durationMetrics:phaseMetrics).map(metric=><tr key={metric.key}><th scope="row">{metric.name}{metric.unit?` (${metric.unit})`:''}</th><td>{display(report.selected[metric.family]?.[metric.key])}</td><td>{display(baseline[metric.family]?.[metric.key])}</td></tr>)}</tbody></table></div></section>;
}

export function QualityIntervals({intervals}:{intervals:QualityReport['uncertainty']['metric_confidence_intervals']}){
 const recorded=intervals.recorded;
 if(!recorded)return <p>{intervals.reason}</p>;
 const rows=Object.entries(recorded).filter(([,value])=>value!==null&&typeof value==='object'&&'lower' in value) as [string,{lower:number|null;upper:number|null;valid_resamples:number}][];
 const names:Record<string,string>={mae:'MAE (days)',rmse:'RMSE (days)',median_absolute_error:'Median absolute error (days)',r2:'R²',auroc:'AUROC',average_precision:'Average precision',brier:'Brier score',log_loss:'Log loss',accuracy:'Phase accuracy',balanced_accuracy:'Balanced accuracy',macro_f1:'Macro F1'};
 return <div className="mq-intervals"><h3>Recorded bootstrap confidence intervals</h3><p>{numeric(recorded.level)?`${display(recorded.level*100,0)}% intervals · `:''}{text(recorded.method)}</p><div className="table-wrap"><table><thead><tr><th>Metric</th><th>Lower</th><th>Upper</th><th>Valid resamples</th></tr></thead><tbody>{rows.map(([key,value])=><tr key={key}><th scope="row">{names[key]||key}</th><td>{display(value.lower)}</td><td>{display(value.upper)}</td><td>{display(value.valid_resamples,0)}</td></tr>)}</tbody></table></div><p>{intervals.reason}</p></div>;
}

export function ModelQuality({projectId}:{projectId?:string}){
 const scope=projectId||(typeof sessionStorage==='undefined'?'':sessionStorage.getItem('cti-project-id')||'');
 const [task,setTask]=useState<Task>('duration'),[split,setSplit]=useState('test'),[attempt,setAttempt]=useState(0);
 const [state,setState]=useState<{key:string;report:QualityReport|null;error:string;loading:boolean}>({key:'',report:null,error:'',loading:true});
 const [downloadError,setDownloadError]=useState(''),[downloading,setDownloading]=useState(false);
 const requestId=useRef(0),key=`${scope}:${task}:${split}`;
 const run=useCallback(()=>setAttempt(n=>n+1),[]);
 useEffect(()=>{
  const id=++requestId.current;setState({key,report:null,error:'',loading:true});setDownloadError('');
  fetchModelQuality(task,split).then(report=>{if(id===requestId.current)setState({key,report,error:'',loading:false})}).catch(error=>{if(id===requestId.current)setState({key,report:null,error:error instanceof Error?error.message:'Quality inspection is unavailable.',loading:false})});
  return()=>{requestId.current++};
 },[key,task,split,attempt]);
 const report=state.key===key?state.report:null,loading=state.key!==key||state.loading;
 const error=state.key===key?state.error:'';
 const download=async(format:'html'|'csv')=>{setDownloading(true);setDownloadError('');try{await downloadQuality(task,split,format)}catch(e){setDownloadError(e instanceof Error?e.message:'Download failed.')}finally{setDownloading(false)}};
 const splitOptions=report?Object.entries(report.split_counts).filter(([,value])=>value.role!=='train').map(([name,value])=>({name,role:value.role})):['test','validation','calibration'].map(name=>({name,role:name==='validation'?'tuning':name}));
 return <section className="mq-root panel" aria-label="Saved model quality">
  <header className="mq-heading"><div className="mq-heading-icon"><BarChart3 size={23}/></div><div><h2>Model quality</h2><p>Inspect the approved model’s saved evaluation evidence.</p></div></header>
  <div className="mq-body"><div className="mq-controls"><label>Prediction task<select value={task} onChange={e=>{setTask(e.target.value as Task);setSplit('test')}}><option value="duration">Duration & prolonged risk</option><option value="phase">Phase consistency</option></select></label><label>Evaluation split<select value={split} onChange={e=>setSplit(e.target.value)}>{splitOptions.map(option=><option key={option.name} value={option.name}>{option.name} · {option.role}</option>)}</select></label><button className="btn primary" disabled={loading} onClick={run}><RefreshCw size={16} className={loading?'mq-spin':''}/>{loading?'Checking evidence…':'Run quality check'}</button></div>
   <p className="mq-note">These metrics describe the model’s labelled training/evaluation cohort. Predictions on an unlabelled upload cannot measure accuracy. Duration errors are measured in days.</p>
   {loading&&<div className="mq-loading" role="status">Rechecking approved artifact checksums and recomputing saved predictions…</div>}
   {error&&<div className="mq-error" role="alert"><strong>Model quality unavailable</strong><p>{error}</p><button className="btn secondary" onClick={run}>Retry quality check</button></div>}
   {report&&<><div className="mq-identity"><div><span className="mq-eyebrow">Approved research model</span><h3>{report.model.name||report.model.id}</h3><p><code>{report.model.id}</code> · branch <strong>{report.model.branch}</strong></p></div><span className="mq-integrity"><ShieldCheck size={17}/>Artifact & manifest verified</span></div>
    <div className="mq-evidence-line"><span><strong>{report.selected.n.toLocaleString()}</strong> labelled evaluation trials</span><span><strong>{report.selected.split}</strong> · {report.selected.split_role}</span><span>{text(report.provenance.source||report.provenance.dataset_name)}</span></div>
    {report.selected_split!=='test'&&<p className="mq-warning">{report.selected.split_role==='calibration'?'Calibration records fit probability transforms or prediction intervals. Diagnostics on this split can be optimistic.':'Tuning records support model selection. These scores are not the final held-out test estimate.'}</p>}
    {report.selected_split==='test'&&report.selected.split_role!=='test'&&<p className="mq-warning">Evaluation group: {report.selected.split_role}. This subgroup evaluation does not establish chronological or prospective accuracy.</p>}
    <QualityMetrics task={report.task} row={report.selected}/>
    <p className="mq-endpoint">{report.endpoint.meaning}{numeric(report.endpoint.prolonged_threshold_days)?` Prolonged outcome: observed duration > ${display(report.endpoint.prolonged_threshold_days,1)} days.`:''} {report.endpoint.probability_semantics}</p>
    <QualityBaseline report={report}/>
    <div className="mq-plots"><QualityConfusion classification={report.selected.classification} title={task==='duration'?'Prolonged outcome · raw probability ≥ 0.5':'Recorded phase versus predicted phase'}/>{report.charts.map((chart,i)=><QualityPlot key={`${chart.title}-${i}`} chart={chart}/>)}</div>
    {report.selected.calibrated_classification&&<section className="mq-calibrated"><h3>Separately saved calibrated probabilities</h3><p>Calibrated Brier: <strong>{display(report.selected.calibrated_classification.brier)}</strong> · log loss: <strong>{display(report.selected.calibrated_classification.log_loss)}</strong>. The main probability metrics above describe raw scores.</p><QualityConfusion classification={report.selected.calibrated_classification} title="Calibrated prolonged outcome · probability ≥ 0.5"/></section>}
    <section className="mq-provenance"><h3>Source, split support & uncertainty</h3><dl><div><dt>Training / evaluation input</dt><dd>{text(report.provenance.dataset_name||report.provenance.source)}</dd></div><div><dt>Input / eligible / excluded</dt><dd>{display(report.cohort.input_rows,0)} / {display(report.cohort.eligible_rows,0)} / {display(report.cohort.excluded_rows,0)}</dd></div><div><dt>Source endpoint</dt><dd>{text(report.provenance.endpoint)}</dd></div><div><dt>Source retrieved</dt><dd>{text(report.provenance.retrieved_at)}</dd></div></dl><div className="table-wrap"><table><thead><tr><th>Split</th><th>Purpose</th><th>Unique trials</th></tr></thead><tbody>{Object.entries(report.split_counts).map(([name,value])=><tr key={name}><th scope="row">{name}</th><td>{value.role}</td><td>{value.n.toLocaleString()}</td></tr>)}</tbody></table></div><p>{report.provenance_scope}</p><QualityIntervals intervals={report.uncertainty.metric_confidence_intervals}/><details><summary>Prediction intervals and metric uncertainty</summary><pre>{JSON.stringify(report.uncertainty,null,2)}</pre></details><details><summary>Artifact identity, reproducibility & checksums</summary><pre>{JSON.stringify({model:report.model,integrity:report.integrity,source:report.provenance,chart_sampling:report.chart_sampling},null,2)}</pre></details><details><summary>Research limitations ({report.warnings.length})</summary><ul>{report.warnings.map((warning,i)=><li key={i}>{warning}</li>)}</ul></details></section>
    <div className="mq-downloads"><button className="btn secondary" disabled={downloading} onClick={()=>void download('html')}><Download size={16}/>Download report</button><button className="btn secondary" disabled={downloading} onClick={()=>void download('csv')}>Metrics CSV</button><button className="btn secondary" onClick={()=>downloadText(JSON.stringify(report,null,2),`${task}-${split}-model-quality.json`,'application/json')}>Evidence JSON</button><small>HTML and CSV downloads recheck the saved evidence.</small></div>{downloadError&&<p className="mq-error" role="alert">{downloadError}</p>}
   </>}
  </div>
 </section>;
}
