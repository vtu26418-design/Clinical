import type {Dataset,Detail,Study,Overview,Experiment} from './types';
import sample from './sample.json';
import researchDemo from './demoResearch.json';
import {pci,planning} from './formulas';
export {pci,pciParts} from './formulas';
export const DEMO = import.meta.env.VITE_DEMO_MODE === 'true';
const BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';
const demoRows:Study[]=sample.map(r=>({...r,...{pci:pci(r).score,complexity:pci(r).category,prolonged_risk:null}}));
const dataset:Dataset={id:'sample-fixture',name:'Sample dataset',row_count:demoRows.length,source:'Bundled software-test fixture',is_fixture:true};
function count(key:string){return demoRows.reduce((a,r)=>({...a,[r[key]]:(a[r[key]]||0)+1}),{} as Record<string,number>)}
export function downloadText(content:string,name:string,type='text/plain'){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([content],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
export function safeCell(value:unknown){let v=String(value??'');if(/^[\s]*[=+@-]/.test(v))v="'"+v;return '"'+v.replaceAll('"','""')+'"'}
async function request<T>(path:string,options:RequestInit={},timeoutMs=60000):Promise<T>{
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),timeoutMs);
 const headers=new Headers(options.headers);if(options.body && !(options.body instanceof FormData))headers.set('Content-Type','application/json');
 const project=sessionStorage.getItem('cti-project-id');if(project)headers.set('X-Project-ID',project);const token=sessionStorage.getItem('cti-api-token');if(token)headers.set('Authorization',`Bearer ${token}`);
 try{const res=await fetch(`${BASE}${path}`,{...options,headers,credentials:'include',signal:controller.signal});if(!res.ok){if(res.status===401)window.dispatchEvent(new Event('cti-session-expired'));const body=await res.json().catch(()=>({detail:`Request failed (${res.status})`}));throw Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body));}return await res.json()}catch(e){if(e instanceof TypeError)throw Error('Cannot reach the API. Start the backend and retry.');throw e}finally{clearTimeout(timeout)}
}
/** Shared project-scoped, cookie-authenticated transport for research evidence. */
export const researchRequest = request;
const scope=(id:string)=>`dataset_id=${encodeURIComponent(id)}`;
const demoScenarios:any[]=[];
const demoWorkspace=(nct:string):any=>{const item=(researchDemo as Record<string,any>)[nct];if(!item)throw Error('Study not found in preview.');return structuredClone(item)};
async function digest(value:unknown){
 const sort=(v:any):any=>Array.isArray(v)?v.map(sort):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().filter(k=>v[k]!==undefined).map(k=>[k,sort(v[k])])):v;
 if(!globalThis.crypto?.subtle)return null;
 const data=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(sort(value))));return [...new Uint8Array(data)].map(b=>b.toString(16).padStart(2,'0')).join('');
}
export const api={
 graphTypes:()=>DEMO?Promise.reject(Error('Cohort graphs require the local API.')):request<any>('/graph-types'),
 graphs:(id:string,graphs:string[],filters:{phase?:string;status?:string}={})=>DEMO?Promise.reject(Error('Full-cohort graphs are available in the local application.')):request<any>('/overview/graphs',{method:'POST',body:JSON.stringify({dataset_id:id,graphs,...filters})}),
 visualizations:(id:string,nct:string)=>DEMO?Promise.reject(Error('Study visualizations require saved study evidence.')):request<any>(`/visualizations/study?${scope(id)}&nct_id=${encodeURIComponent(nct)}`),
 explain:(id:string,nct:string)=>DEMO?Promise.reject(Error('Saved model explanations require the local API.')):request<any>('/explain',{method:'POST',body:JSON.stringify({dataset_id:id,nct_id:nct})}),
 pipelineStatus:(id:string)=>DEMO?Promise.resolve({status:'unavailable',reason:'No experiment lifecycle in the interface preview.'}):request<any>(`/pipeline-status?${scope(id)}`),
 health:()=>DEMO?Promise.resolve({status:'ok',version:'5.0.0',ai_provider:'disabled',sample_data:true,openai_configured:false}):request<any>('/health'),
 researchWorkspace:(id:string,nct:string)=>DEMO?Promise.resolve(demoWorkspace(nct)):request<any>(`/research/workspace?${scope(id)}&nct_id=${encodeURIComponent(nct)}`),
 scenarios:(id:string,nct:string)=>DEMO?Promise.resolve({items:structuredClone(demoScenarios.filter(s=>s.provenance.dataset_id===id&&s.base.study.nct_id===nct))}):request<any>(`/research/scenarios?${scope(id)}&nct_id=${encodeURIComponent(nct)}`),
 scenario:async(id:string,nct:string,overrides:Record<string,unknown>,assumptions:{sites:number;monthly_rate_per_site:number;startup_months:number;followup_months:number},name:string,model_name='recommended')=>{
  if(!DEMO)return request<any>('/research/scenarios',{method:'POST',body:JSON.stringify({dataset_id:id,nct_id:nct,overrides,planning:assumptions,name,model_name})});
  const w=demoWorkspace(nct),study={...w.study,...overrides};
  if(study.enrollment===null||study.enrollment===undefined||study.enrollment==='')throw Error('Enter target enrollment before calculating a scenario.');
  const p=planning(Number(study.enrollment),Number(assumptions.sites),Number(assumptions.monthly_rate_per_site),Number(assumptions.startup_months),Number(assumptions.followup_months));
  const result:any={id:crypto.randomUUID(),name,created_at:new Date().toISOString(),base:{study:w.study,pci:w.pci,duration:w.duration},scenario:{study,pci:pci(study),duration:w.duration},planning:p,changes:{pci:pci(study).score-w.pci.score,duration_days:null,probability:null},warning:'Hypothetical fixture scenario. Planning uses assumptions; no fitted predictions. Preview history lasts until this page is refreshed.',provenance:w.provenance};
  result.evidence_sha256=await digest(result);demoScenarios.unshift(structuredClone(result));return result;
 },
 evidence:async(id:string,nct:string)=>{
  if(!DEMO)return request<any>(`/research/evidence?${scope(id)}&nct_id=${encodeURIComponent(nct)}`);
  const result:any={workspace:demoWorkspace(nct),scenarios:structuredClone(demoScenarios.filter(s=>s.provenance.dataset_id===id&&s.base.study.nct_id===nct)),generated_at:new Date().toISOString(),scope:'Software-test fixture evidence only; preview scenario history is held in this page memory.'};result.evidence_sha256=await digest(result);return result;
 },
 datasets:()=>DEMO?Promise.resolve({items:[dataset],active_default:dataset.id}):request<{items:Dataset[];active_default:string}>('/datasets'),
 overview:(id:string)=>DEMO?Promise.resolve({dataset,total_studies:demoRows.length,median_pci:[...demoRows].sort((a,b)=>a.pci!-b.pci!)[2].pci!,phase_counts:count('phase'),status_counts:count('status'),enrollment_total:demoRows.reduce((s,r)=>s+(r.enrollment||0),0),quality:{missingness:Object.fromEntries(['brief_summary','eligibility_criteria','enrollment','completion_date','start_date'].map(k=>[k,demoRows.filter(r=>r[k]===undefined||r[k]===null||r[k]==='').length/demoRows.length]))},predictions_available:false} as Overview):request<Overview>(`/overview?${scope(id)}`),
 studies:(id:string,params:Record<string,string|number>={})=>{if(DEMO){let rows=demoRows.filter(r=>(!params.q||[r.nct_id,r.title].join(' ').toLowerCase().includes(String(params.q).toLowerCase()))&&(!params.phase||r.phase===params.phase)&&(!params.status||r.status===params.status));const k=String(params.sort_by||'nct_id');rows=rows.sort((a,b)=>{const x=a[k],y=b[k];return (typeof x==='number'?x-y:String(x).localeCompare(String(y)))*(params.sort_dir==='desc'?-1:1)});return Promise.resolve({items:rows.slice(Number(params.offset||0),Number(params.offset||0)+Number(params.limit||25)),total:rows.length})}return request<{items:Study[];total:number}>(`/studies?${scope(id)}&${new URLSearchParams(Object.fromEntries(Object.entries(params).map(([k,v])=>[k,String(v)])))}`)},
 detail:(id:string,nct:string)=>DEMO?Promise.resolve({study:demoRows.find(r=>r.nct_id===nct)!,pci:pci(demoRows.find(r=>r.nct_id===nct)!),prediction:{available:false,reason:'Train a model on a sufficiently large dataset in the full local application.'}} as Detail):request<Detail>(`/studies/${encodeURIComponent(nct)}?${scope(id)}`),
 experiments:()=>DEMO?Promise.resolve({items:[] as Experiment[]}):request<{items:Experiment[]}>('/experiments'),
 readiness:(id:string)=>DEMO?Promise.resolve({duration:{ready:false,reason:'Run the full local app to train on real data.'},phase:{ready:false,reason:'Run the full local app to train on real data.'}}):request<any>(`/readiness?${scope(id)}`),
 starter:()=>DEMO?Promise.reject(Error('The 800-record starter cohort is included in the full project ZIP. Open the local app to load it.')):request<Dataset>('/datasets/starter',{method:'POST'}),
 phasePredict:(id:string,nct_id:string)=>DEMO?Promise.reject(Error('Phase predictions require a trained model in the full local app.')):request<any>('/phase-predictions',{method:'POST',body:JSON.stringify({dataset_id:id,nct_id})}),
 predict:(id:string,nct_id:string,model_name:string)=>DEMO?Promise.reject(Error('Duration predictions require a trained model in the full local app.')):request<any>('/predictions',{method:'POST',body:JSON.stringify({dataset_id:id,nct_id,model_name})}),
 phaseTrain:(id:string)=>DEMO?Promise.reject(Error('Phase training runs in the full local app. The Academy works in this preview.')):request<Experiment>('/phase-experiments',{method:'POST',body:JSON.stringify({dataset_id:id})}),
 artifact:async(id:string,name:string)=>{const headers=new Headers();const project=sessionStorage.getItem('cti-project-id');if(project)headers.set('X-Project-ID',project);const token=sessionStorage.getItem('cti-api-token');if(token)headers.set('Authorization',`Bearer ${token}`);const res=await fetch(`${BASE}/experiments/${encodeURIComponent(id)}/files/${encodeURIComponent(name)}`,{headers,credentials:'include'});if(!res.ok)throw Error('Report is unavailable.');downloadText(await res.text(),name,name.endsWith('.csv')?'text/csv':'application/json')},
 train:(id:string,enableCatboost=false,catboostSearch:'basic'|'expanded'='basic')=>DEMO?Promise.reject(Error('Training runs in the full local app. This browser preview uses five software-test fixtures.')):request<Experiment>('/experiments',{method:'POST',body:JSON.stringify({dataset_id:id,enable_catboost:enableCatboost,catboost_search:catboostSearch})}),
 upload:(file:File,name:string)=>{if(DEMO)return Promise.reject(Error('Dataset uploads run in the full local app. No files are sent from this preview.'));const body=new FormData();body.append('file',file);if(name)body.append('name',name);return request<Dataset>('/datasets/upload',{method:'POST',body})},
 importRegistry:(query:string,max_studies:number)=>DEMO?Promise.reject(Error('Connect the local backend to import live ClinicalTrials.gov records.')):request<Dataset>('/datasets/import/clinicaltrials',{method:'POST',body:JSON.stringify({query,max_studies})}),
 chat:(id:string,message:string,nct_id?:string,provider?:string)=>DEMO?Promise.reject(Error('The assistant runs in the local app after you configure an OpenAI, Gemini, Claude or compatible service key.')):request<{reply:string;provider:string;provider_id:string;model:string;fallback_used:boolean}>('/assistant',{method:'POST',body:JSON.stringify({dataset_id:id,message,nct_id,provider})},120000),
 export:async(id:string,format:'csv'|'html')=>{if(DEMO){if(format==='html'){window.print();return}const keys=['nct_id','title','phase','status','enrollment','pci'];downloadText([keys,...demoRows.map(r=>keys.map(k=>r[k]))].map(row=>row.map(safeCell).join(',')).join('\n'),'sample-studies.csv','text/csv');return}const headers=new Headers();const project=sessionStorage.getItem('cti-project-id');if(project)headers.set('X-Project-ID',project);const token=sessionStorage.getItem('cti-api-token');if(token)headers.set('Authorization',`Bearer ${token}`);const res=await fetch(`${BASE}/exports/${format==='csv'?'studies.csv':'report.html'}?${scope(id)}`,{headers,credentials:'include'});if(!res.ok)throw Error('Export failed. Check the backend connection.');downloadText(await res.text(),`cti-report.${format}`,format==='csv'?'text/csv':'text/html')}
};
