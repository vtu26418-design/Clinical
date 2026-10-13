import type {ReactNode} from 'react';
import {nice,number} from '../Shared';

export type GraphData = {
 status:'available'|'partial'|'unavailable'; denominator:number; reporting_rows:number; missing_rows:number;
 units?:string;method?:string;reason?:string;[key:string]:any;
};
const colors=['#087f8c','#81c8cf','#62a9d2','#8cc3e8','#a5b6c4','#547c98'];
const label=(v:unknown)=>nice(v).replaceAll('PHASE','Phase ').replaceAll('  ',' ');
const shortLabel=(v:unknown)=>label(v).replace(/1000/g,'1k').replace(/5000/g,'5k');
const W=640,H=252,L=65,R=18,T=16,B=57;
const ticks=(max:number)=>Array.from({length:5},(_,i)=>max*i/4);
function Canvas({title,children,xLabel,yLabel}:{title:string;children:ReactNode;xLabel?:string;yLabel?:string}){
 return <svg className="cti-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={title} preserveAspectRatio="xMidYMid meet"><title>{title}</title>{children}{xLabel&&<text className="axis-title" x={(L+W-R)/2} y={H-3} textAnchor="middle">{xLabel}</text>}{yLabel&&<text className="axis-title" transform={`translate(16 ${(T+H-B)/2}) rotate(-90)`} textAnchor="middle">{yLabel}</text>}</svg>;
}
function Grid({max,yLabel}:{max:number;yLabel?:string}){
 const y=(v:number)=>H-B-v/max*(H-B-T);
 return <>{ticks(max).map(v=><g key={v}><line x1={L} x2={W-R} y1={y(v)} y2={y(v)} className="gridline"/><text x={L-9} y={y(v)+4} textAnchor="end">{number(v)}</text></g>)}<line x1={L} x2={W-R} y1={H-B} y2={H-B} className="axis"/>{yLabel&&<title>{yLabel}</title>}</>;
}
function Bars({data,title,xLabel,yLabel='Studies',multicolor=false}:{data:GraphData;title:string;xLabel?:string;yLabel?:string;multicolor?:boolean}){
 const labels:string[]=data.labels||[],values:number[]=data.values||[];
 const max=Math.ceil(Math.max(1,...values.filter(v=>typeof v==='number'))*1.13/4)*4,slot=(W-L-R)/Math.max(1,labels.length),barWidth=Math.max(2,slot*(labels.length>15?.84:.64));
 return <Canvas title={title} xLabel={xLabel} yLabel={yLabel}><Grid max={max}/>{labels.map((v,i)=>{const h=(values[i]||0)/max*(H-B-T),x=L+i*slot+(slot-barWidth)/2;return <g key={`${v}-${i}`}><rect x={x} y={H-B-h} width={barWidth} height={h} rx={1} fill={multicolor?colors[i%colors.length]:'#087f8c'}><title>{label(v)}: {number(values[i])} {data.units||''}</title></rect>{labels.length<9&&<text x={x+barWidth/2} y={H-B-h-7} textAnchor="middle" className="bar-value">{number(values[i])}</text>}{(labels.length<10||i%Math.ceil(labels.length/7)===0)&&<text x={x+barWidth/2} y={H-B+18} textAnchor="middle" className={labels.length>8?'small-tick':''}>{shortLabel(v)}</text>}</g>})}</Canvas>;
}
function Scatter({data}:{data:GraphData}){
 const points:any[]=(data.points||[]).filter((p:any)=>typeof p.enrollment==='number'&&Number.isFinite(p.enrollment)&&typeof p.pci==='number'&&Number.isFinite(p.pci)),maxX=Math.max(1,...points.map(p=>p.enrollment)),logMax=Math.log10(maxX+1),x=(v:number)=>L+Math.log10(v+1)/logMax*(W-L-R),y=(v:number)=>H-B-v/100*(H-B-T),powers=[0,...Array.from({length:Math.floor(logMax)+1},(_,i)=>10**i)].filter(v=>v<=maxX);
 return <Canvas title="Reported enrollment versus protocol complexity" xLabel="Enrollment (participants · log scale)" yLabel="PCI score"><Grid max={100}/>{powers.map(v=><g key={v}><line x1={x(v)} x2={x(v)} y1={T} y2={H-B} className="gridline"/><text x={x(v)} y={H-B+18} textAnchor="middle">{number(v)}</text></g>)}{points.map((p,i)=><circle key={`${p.nct_id}-${i}`} cx={x(Number(p.enrollment))} cy={y(Number(p.pci))} r={2.8} fill="#087f8c" opacity=".65"><title>{p.nct_id} · {label(p.phase)} · enrollment {number(p.enrollment)} · PCI {number(p.pci)}</title></circle>)}</Canvas>;
}
function DurationBox({data}:{data:GraphData}){
 const groups:any[]=data.groups||[],max=Math.max(1,...groups.flatMap(g=>g.values||[]))*1.05,slot=(W-L-R)/Math.max(1,groups.length),y=(v:number)=>H-B-v/max*(H-B-T);
 return <Canvas title="Observed duration quartiles by phase" yLabel="Observed duration (days)" xLabel="Reported phase"><Grid max={max}/>{groups.map((g,i)=>{const x=L+slot*(i+.5),values:number[]=g.values||[];if(!values.length)return null;const low=Math.min(...values),high=Math.max(...values),width=Math.min(50,slot*.5);return <g key={g.phase}><title>{label(g.phase)} · n={g.n} · median {number(g.median)} days · Q1 {number(g.q1)} · Q3 {number(g.q3)}</title><line x1={x} x2={x} y1={y(low)} y2={y(high)} stroke="#547c98"/><line x1={x-10} x2={x+10} y1={y(low)} y2={y(low)} stroke="#547c98"/><line x1={x-10} x2={x+10} y1={y(high)} y2={y(high)} stroke="#547c98"/><rect x={x-width/2} y={y(g.q3)} width={width} height={Math.max(1,y(g.q1)-y(g.q3))} fill="#a7d9df" stroke="#087f8c"/><line x1={x-width/2} x2={x+width/2} y1={y(g.median)} y2={y(g.median)} stroke="#10283f" strokeWidth={2}/><text x={x} y={H-B+18} textAnchor="middle">{label(g.phase)}</text><text x={x} y={H-B+34} textAnchor="middle" className="small-tick">n={g.n}</text></g>})}</Canvas>;
}
function Missingness({data}:{data:GraphData}){
 return <div className="cti-missing-bars">{(data.fields||[]).map((f:any)=><div key={f.field}><span>{label(f.field)}</span><div className="cti-missing-track"><span style={{width:`${Math.max(0,Math.min(100,Number(f.missing_fraction)*100))}%`}}/></div><b>{number(Number(f.missing_fraction)*100)}%</b><small>{number(f.missing_rows)} missing</small></div>)}</div>;
}
function Components({data}:{data:GraphData}){
 return <div className="cti-evidence-table"><table><thead><tr><th>Component</th><th>Mean</th><th>Median</th><th>Reported</th><th>Missing</th></tr></thead><tbody>{(data.dimensions||[]).map((d:any)=><tr key={d.dimension}><th>{label(d.dimension)}</th><td>{number(d.mean)}</td><td>{number(d.median)}</td><td>{number(d.reporting_rows)}</td><td>{number(d.missing_rows)}</td></tr>)}</tbody></table></div>;
}
function Timeline({data}:{data:GraphData}){
 const trials:any[]=data.trials||[];
 return <div className="cti-evidence-table"><table><thead><tr><th>Study</th><th>Start</th><th>Completion</th><th>Days</th></tr></thead><tbody>{trials.slice(0,10).map(t=><tr key={t.nct_id}><th>{t.nct_id}</th><td>{t.start_date||t.start||'—'}<small>{t.start_precision||t.start_date_precision}</small></td><td>{t.completion_date||t.completion||'—'}<small>{t.completion_precision||t.completion_date_precision}</small></td><td>{number(t.observed_duration_days)}</td></tr>)}</tbody></table>{trials.length>10&&<p className="cti-chart-note">First 10 of {number(trials.length)} reported studies. Export contains all returned rows.</p>}</div>;
}
function ModelComparison({data}:{data:GraphData}){
 const models:any[]=data.models||[],duration=models.filter(m=>typeof m.metrics?.regression?.mae==='number'&&Number.isFinite(m.metrics.regression.mae));
 const max=Math.max(1,...duration.map(m=>m.metrics.regression.mae));
 return <div className="cti-model-comparison"><div className="cti-model-error-bars" role="img" aria-label="Recorded held-out duration mean absolute error in days; lower is better">{duration.map((m,i)=><div key={`${m.experiment_id}-${m.model_name}-${i}`}><span title={m.model_name}>{m.model_name.replaceAll('structured_','').replaceAll('_',' ')}</span><div><i style={{width:`${m.metrics.regression.mae/max*100}%`}}/></div><strong>{number(m.metrics.regression.mae)} d</strong></div>)}</div><details className="cti-model-metrics"><summary>Complete held-out metrics</summary><div className="cti-evidence-table"><table><thead><tr><th>Model</th><th>Task</th><th>Test n</th><th>MAE / Accuracy</th><th>Brier</th></tr></thead><tbody>{models.map((m,i)=><tr key={`${m.experiment_id}-${m.model_name}-${i}`}><th>{m.model_name}<small>{m.run_id||m.experiment_id}</small></th><td>{m.task}</td><td>{number(m.n??m.metrics?.n)}</td><td>{m.task==='phase'?number(m.metrics?.accuracy):number(m.metrics?.regression?.mae)}</td><td>{number(m.metrics?.classification?.brier)}</td></tr>)}</tbody></table></div></details></div>;
}
export function GraphContent({id,data,title}:{id:string;data?:GraphData;title:string}){
 if(!data||data.status==='unavailable')return <div className="cti-graph-empty"><strong>Evidence unavailable</strong><span>{data?.reason||'This graph needs reported source fields or saved model evidence.'}</span></div>;
 if(id==='pci_scatter')return <Scatter data={data}/>;
 if(id==='duration_box')return <DurationBox data={data}/>;
 if(id==='missingness')return <Missingness data={data}/>;
 if(id==='pci_components')return <Components data={data}/>;
 if(id==='timeline_gantt')return <Timeline data={data}/>;
 if(id==='model_comparison')return <ModelComparison data={data}/>;
 const axis=id==='enrollment_histogram'?'Enrollment (participants)':id==='pci_distribution'?'PCI score':id==='start_year_activity'?'Reported start year':'Reported category';
 return <Bars data={data} title={title} xLabel={axis} yLabel={id==='enrollment_by_phase'?'Total reported enrollment':'Studies'} multicolor={id==='phase_distribution'||id==='status_distribution'}/>;
}
