import {useCallback,useEffect,useMemo,useState} from 'react';
import {ArrowDown,ArrowUp,BarChart3,Check,ChevronDown,ChevronLeft,ChevronRight,Download,GripVertical,Maximize2,Minimize2,SlidersHorizontal,X} from 'lucide-react';
import {api,downloadText,safeCell} from '../../api';
import type {Dataset,Overview,Study} from '../../types';
import {Modal,Notice,SearchBox,StudyTable,nice,number} from '../Shared';
import {GraphContent} from './GraphContent';
import type {GraphData} from './GraphContent';
import './overview.css';

const GRAPH_TYPES=[
 {id:'phase_distribution',label:'Phase distribution'}, {id:'status_distribution',label:'Status distribution'},
 {id:'enrollment_histogram',label:'Enrollment distribution'}, {id:'pci_distribution',label:'Protocol complexity'},
 {id:'pci_scatter',label:'Enrollment vs complexity'}, {id:'duration_box',label:'Observed duration'},
 {id:'enrollment_by_phase',label:'Enrollment by phase'}, {id:'pci_components',label:'PCI components'},
 {id:'timeline_gantt',label:'Observed trial dates'}, {id:'missingness',label:'Missing data'},
 {id:'start_year_activity',label:'Start-year activity'}, {id:'model_comparison',label:'Model comparison'},
];
const DEFAULT_GRAPHS=['phase_distribution','enrollment_histogram','pci_distribution','pci_scatter'];
type GraphResponse={dataset_id:string;source_sha256?:string;source_rows:number;row_count:number;filters:Record<string,string>;selected_graphs:string[];computed_data:Record<string,GraphData>};
type Props={
 dataset:Dataset;overview:Overview;rows:Study[];total:number;query:string;setQuery:(value:string)=>void;
 phase:string;setPhase:(value:string)=>void;status:string;setStatus:(value:string)=>void;
 offset:number;setOffset:(value:number)=>void;onSelect:(id:string)=>void;onNavigate:(route:string)=>void;
 selected:string[];onCompare:(id:string)=>void;onShowCompare:()=>void;projectId:string;
};
function storedGraphs(key:string){try{const saved=JSON.parse(localStorage.getItem(key)||'null');if(Array.isArray(saved))return [...new Set(saved.filter(id=>GRAPH_TYPES.some(g=>g.id===id)))];}catch{}return DEFAULT_GRAPHS;}
function csvRows(graph:GraphData):Record<string,unknown>[] {
 if(Array.isArray(graph.labels))return graph.labels.map((label:string,i:number)=>({label,value:graph.values?.[i],reporting_count:graph.reporting_counts?.[i],...(graph.bins?.[i]&&typeof graph.bins[i]==='object'?graph.bins[i]:{})}));
 const value=graph.points||graph.groups||graph.dimensions||graph.trials||graph.fields||graph.models||[];
 return value.map((r:any)=>Object.fromEntries(Object.entries(r).map(([k,v])=>[k,typeof v==='object'&&v!==null?JSON.stringify(v):v])));
}
function exportGraph(id:string,data:GraphData,response:GraphResponse,format:'json'|'csv'){
 const name=`cti-${id}-${response.dataset_id}`;
 if(format==='json'){downloadText(JSON.stringify({dataset_id:response.dataset_id,source_sha256:response.source_sha256,source_rows:response.source_rows,row_count:response.row_count,filters:response.filters,graph:data},null,2),`${name}.json`,'application/json');return;}
 const records:Record<string,unknown>[]=csvRows(data).map(row=>({dataset_id:response.dataset_id,source_sha256:response.source_sha256,filtered_rows:response.row_count,status:data.status,denominator:data.denominator,reporting_rows:data.reporting_rows,missing_rows:data.missing_rows,units:data.units,method:data.method,...row})),headers=[...new Set(records.flatMap(r=>Object.keys(r)))];
 downloadText([headers,...records.map(r=>headers.map(k=>r[k]))].map(row=>row.map(safeCell).join(',')).join('\n'),`${name}.csv`,'text/csv');
}
export function EnhancedOverview({dataset,overview,rows,total,query,setQuery,phase,setPhase,status,setStatus,offset,setOffset,onSelect,onNavigate,selected,onCompare,onShowCompare,projectId}:Props){
 const storageKey=`cti.overview.v5202.${projectId}.${dataset.id}`;
 const [graphs,setGraphs]=useState<string[]>(()=>storedGraphs(storageKey));
 const [draft,setDraft]=useState(graphs),[customizing,setCustomizing]=useState(false),[response,setResponse]=useState<GraphResponse|null>(null),[busy,setBusy]=useState(true),[error,setError]=useState(''),[retry,setRetry]=useState(0),[fullscreen,setFullscreen]=useState<string|null>(null),[dragged,setDragged]=useState<string|null>(null);
 const [metadata,setMetadata]=useState<Record<string,{label:string;description?:string}>>({});
 useEffect(()=>{setGraphs(storedGraphs(storageKey));setResponse(null)},[storageKey]);
 useEffect(()=>{localStorage.setItem(storageKey,JSON.stringify(graphs))},[storageKey,graphs]);
 useEffect(()=>{let alive=true;api.graphTypes().then(r=>{if(alive)setMetadata(Object.fromEntries((r.graph_types||[]).map((g:any)=>[g.id,g])))}).catch(()=>{});return()=>{alive=false}},[]);
 const graphIds=graphs.join('|');
 useEffect(()=>{let alive=true;setBusy(true);setError('');api.graphs(dataset.id,graphs,{...(phase?{phase}:{}),...(status?{status}:{})}).then(r=>{if(alive){setResponse(r);setBusy(false)}}).catch(e=>{if(alive){setResponse(null);setError(e.message);setBusy(false)}});return()=>{alive=false}},[dataset.id,graphIds,phase,status,retry]);
 const closeFullscreen=useCallback(()=>setFullscreen(null),[]);
 const moveGraph=(id:string,direction:number)=>setGraphs(current=>{const index=current.indexOf(id),target=index+direction;if(target<0||target>=current.length)return current;const next=[...current];[next[index],next[target]]=[next[target],next[index]];return next;});
 const dropGraph=(id:string)=>{if(dragged&&dragged!==id)setGraphs(current=>{const next=current.filter(g=>g!==dragged);next.splice(next.indexOf(id),0,dragged);return next});setDragged(null)};
 const chartLabel=(id:string)=>GRAPH_TYPES.find(g=>g.id===id)?.label||metadata[id]?.label||nice(id);
 const graphCards=useMemo(()=>graphs.map(id=>({id,title:chartLabel(id),data:response?.computed_data?.[id]})),[graphIds,response,metadata]);
 const filteredCount=response?.row_count??total;
 const completed=Object.entries(overview.status_counts).filter(([s])=>s.toUpperCase()==='COMPLETED').reduce((sum,[,value])=>sum+value,0);
 function graphBody(id:string,title:string,data?:GraphData,large=false){return <section className={`cti-graph-card ${large?'cti-graph-large':''}`} data-testid={`graph-${id}`} draggable={!large} onDragStart={event=>{setDragged(id);event.dataTransfer.setData('text/plain',id)}} onDragOver={e=>e.preventDefault()} onDrop={()=>dropGraph(id)} onDragEnd={()=>setDragged(null)}><header><div className="cti-graph-heading"><GripVertical size={15} aria-hidden="true"/><h2>{title}</h2></div><div className="cti-graph-actions">{!large&&<><button className="icon-btn" aria-label={`Move ${title} earlier`} disabled={graphs.indexOf(id)===0} onClick={()=>moveGraph(id,-1)}><ArrowUp size={14}/></button><button className="icon-btn" aria-label={`Move ${title} later`} disabled={graphs.indexOf(id)===graphs.length-1} onClick={()=>moveGraph(id,1)}><ArrowDown size={14}/></button></>}<details className="cti-export-menu"><summary aria-label={`Export ${title}`} title="Export graph data"><Download size={16}/></summary><div><button disabled={!data||!response} onClick={()=>data&&response&&exportGraph(id,data,response,'csv')}>Export CSV</button><button disabled={!data||!response} onClick={()=>data&&response&&exportGraph(id,data,response,'json')}>Export JSON</button></div></details><button className="icon-btn" aria-label={large?`Close fullscreen ${title}`:`Fullscreen ${title}`} onClick={()=>setFullscreen(large?null:id)}>{large?<Minimize2 size={16}/>:<Maximize2 size={16}/>}</button></div></header><div className="cti-graph-content">{busy?<div className="cti-graph-empty" role="status"><span className="spinner"/>Loading cohort evidence…</div>:<GraphContent id={id} data={data} title={title}/>}</div>{data&&<footer><span>{id==='model_comparison'?`${number(data.reporting_rows)} saved test observations`:`${number(data.reporting_rows)} reported / ${number(data.denominator)} studies${data.missing_rows>0?` · ${number(data.missing_rows)} missing`:''}`}</span><details><summary>Method</summary><p>{data.method||metadata[id]?.description||'Computed from selected source records.'}</p>{data.status==='partial'&&<p>Partial source coverage.</p>}<p>Units: {data.units||'Not supplied'}</p></details></footer>}</section>}
 return <div className="cti-overview" data-testid="evidence-overview"><div className="cti-overview-heading"><h1>Overview</h1><div className="inline-actions"><button className="btn primary" disabled={selected.length<2} onClick={onShowCompare}><SlidersHorizontal size={16}/>Compare studies{selected.length?` (${selected.length})`:''}</button><div className="cti-customize"><button className="btn secondary" aria-expanded={customizing} onClick={()=>{setDraft(graphs);setCustomizing(v=>!v)}}><BarChart3 size={16}/>Customize graphs<ChevronDown size={14}/></button>{customizing&&<div className="cti-customize-panel" role="group" aria-label="Choose overview graphs"><div className="cti-customize-title"><strong>Overview graphs</strong><button className="icon-btn" aria-label="Close graph selection" onClick={()=>setCustomizing(false)}><X size={15}/></button></div>{GRAPH_TYPES.map(g=><label key={g.id}><input type="checkbox" checked={draft.includes(g.id)} onChange={e=>setDraft(current=>e.target.checked?[...current,g.id]:current.filter(id=>id!==g.id))}/><span>{g.label}</span></label>)}<div className="cti-customize-footer"><button className="text-btn" onClick={()=>setDraft(DEFAULT_GRAPHS)}>Reset</button><button className="btn primary" onClick={()=>{setGraphs(draft);setCustomizing(false)}}><Check size={15}/>Apply</button></div></div>}</div></div></div>
 <div className="cti-cohort-stats"><div><span>Studies</span><strong>{number(overview.total_studies)}</strong></div><div><span>Reported phases</span><strong>{number(Object.keys(overview.phase_counts).filter(k=>!['Not reported','Unknown','NA','N/A'].includes(k)).length)}</strong></div><div><span>Completed</span><strong>{number(completed)}</strong></div><button onClick={()=>onNavigate('models')}><span>Saved model</span><strong>{overview.predictions_available?'Available':'Unavailable'}</strong><small>Open model registry</small></button></div>
 <div className="cti-cohort-filters"><label>Phase<select aria-label="Overview phase filter" value={phase} onChange={e=>{setPhase(e.target.value);setOffset(0)}}><option value="">All phases</option>{Object.keys(overview.phase_counts).map(p=><option key={p} value={p}>{nice(p)}</option>)}</select></label><label>Status<select aria-label="Overview status filter" value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}><option value="">All statuses</option>{Object.keys(overview.status_counts).map(s=><option key={s} value={s}>{nice(s)}</option>)}</select></label><span>{number(filteredCount)} studies in view</span>{(phase||status)&&<button className="text-btn" onClick={()=>{setPhase('');setStatus('');setOffset(0)}}>Clear filters</button>}</div>
 {error&&<Notice kind="error">{error} <button className="text-btn" onClick={()=>setRetry(n=>n+1)}>Retry graphs</button></Notice>}
 {graphs.length?<div className="cti-graph-grid" aria-busy={busy}>{graphCards.map(({id,title,data})=><div key={id} className={dragged===id?'cti-dragging':''}>{graphBody(id,title,data)}</div>)}</div>:<section className="cti-graph-empty cti-empty-selection"><strong>No graphs selected</strong><button className="btn secondary" onClick={()=>{setDraft(graphs);setCustomizing(true)}}>Choose graphs</button></section>}
 <section className="cti-comparison-panel"><header><h2>Study comparison</h2><SearchBox value={query} onChange={v=>{setQuery(v);setOffset(0)}}/></header><StudyTable rows={rows} selected={selected} onCompare={onCompare} onSelect={onSelect}/><footer><span>Select up to 3 studies</span><div className="pagination"><span>{total?offset+1:0}–{Math.min(offset+25,total)} of {number(total)}</span><button className="icon-btn" aria-label="Previous overview studies" disabled={!offset} onClick={()=>setOffset(Math.max(0,offset-25))}><ChevronLeft size={17}/></button><button className="icon-btn" aria-label="Next overview studies" disabled={offset+25>=total} onClick={()=>setOffset(offset+25)}><ChevronRight size={17}/></button></div></footer></section>
 {response&&<details className="cti-cohort-provenance"><summary>Source & method</summary><p>{dataset.name} · {number(response.source_rows)} source records · {number(response.row_count)} filtered records</p><p>All graphs aggregate the selected dataset on the server. Search narrows the study table; phase and status apply to the graphs and table.</p>{response.source_sha256&&<p>SHA-256 <code>{response.source_sha256}</code></p>}<p>PCI describes protocol complexity. It is not an outcome probability. Observed duration requires sufficiently precise reported dates.</p></details>}
 {fullscreen&&<Modal title={chartLabel(fullscreen)} onClose={closeFullscreen} wide>{graphBody(fullscreen,chartLabel(fullscreen),response?.computed_data?.[fullscreen],true)}</Modal>}
 </div>;
}
