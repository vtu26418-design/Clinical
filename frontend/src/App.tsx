import {useCallback,useEffect,useState} from 'react';
import {Activity,CheckCircle2,ChevronDown,ChevronLeft,ChevronRight,Database,Info,Menu,Upload,X} from 'lucide-react';
import {AnimatedPipeline,TrialTimeline,XAIAnimations,RecruitmentJourney,WhatIfSimulator,MultimodalFusion} from './components/animations';
import {EnhancedOverview} from './components/overview';
import {RoleManager} from './components/auth';
import {ResearchHome} from './v52/ResearchHome';
import {ResearchSources} from './v52/ResearchSources';
import {VerificationPanel} from './v52/Verification';
import {api,DEMO} from './api';
import {WorkspaceBar,usePlatform,PlatformSettings,AdditionalImports} from './v5';
import {PredictionStudio,ModelRegistry} from './v5/PredictionStudio';
import {ProtocolLab} from './v5/ProtocolLab';
import type {Dataset,Detail,Overview as OverviewType,Study} from './types';
import {Complexity} from './components/Complexity';
import {DataManager} from './components/DataManager';
import {Experiments} from './components/Experiments';
import {PhaseAcademy} from './components/PhaseAcademy';
import {PhaseModels} from './components/PhaseModels';
import {Assistant} from './components/Assistant';
import {ResearchHub} from './components/ResearchHub';
import {DigitalTwin} from './components/DigitalTwin';
import {ValidationLab} from './components/ValidationLab';
import {FormulaStudio} from './components/FormulaStudio';
import {DetailBody,Empty,ExportButton,Modal,Notice,SearchBox,StudyTable,nice,number} from './components/Shared';
import {navigation as nav,coreRoutes,evidenceRoutes,titles} from './v5202/navigation';
import './v5202/design.css';
export default function App(){
 const {project,user}=usePlatform();
 const capabilities=(project as typeof project & {capabilities?:Record<string,boolean>}).capabilities;
 const allowed=(key:string,fallback:boolean)=>capabilities?.[key]??fallback;
 const canWrite=allowed('write_research',['owner','researcher'].includes(project.role)),isOwner=allowed('train_models',project.role==='owner'),canChat=allowed('chat',project.role!=='viewer'),canScenario=allowed('run_scenarios',['owner','researcher'].includes(project.role)),canManage=allowed('manage_members',project.role==='owner');
 const [moreOpen,setMoreOpen]=useState(false);
 const [autoPredict,setAutoPredict]=useState(false);
 const [scenarioModel,setScenarioModel]=useState('recommended');
 const visibleNav=nav.filter(n=>(n[0]!=='experiments'||isOwner)&&(n[0]!=='assistant'||canChat)&&(!['digital-twin','what-if'].includes(n[0])||canScenario)&&(n[0]!=='roles'||canManage)&&(n[0]!=='data'||canWrite));
 const [route,setRoute]=useState(()=>nav.some(n=>n[0]===location.hash.slice(1))?location.hash.slice(1):'overview'),[mobile,setMobile]=useState(false),[datasets,setDatasets]=useState<Dataset[]>([]),[datasetId,setDatasetId]=useState(()=>sessionStorage.getItem(`cti-dataset-${project.id}`)||'sample-fixture'),[overview,setOverview]=useState<OverviewType|null>(null),[health,setHealth]=useState<any>({}),[rows,setRows]=useState<Study[]>([]),[allRows,setAllRows]=useState<Study[]>([]),[total,setTotal]=useState(0),[query,setQuery]=useState(''),[phase,setPhase]=useState(''),[status,setStatus]=useState(''),[sort,setSort]=useState('nct_id'),[offset,setOffset]=useState(0),[error,setError]=useState(''),[loading,setLoading]=useState(true),[refresh,setRefresh]=useState(0),[detail,setDetail]=useState<Detail|null>(null),[detailBusy,setDetailBusy]=useState(false),[selected,setSelected]=useState(''),[compare,setCompare]=useState<string[]>([]),[showCompare,setShowCompare]=useState(false),[settings,setSettings]=useState(false),[token,setToken]=useState(()=>sessionStorage.getItem('cti-api-token')||''),[toast,setToast]=useState('');
 const switchDataset=(id:string)=>{setDatasetId(id);sessionStorage.setItem(`cti-dataset-${project.id}`,id);setOffset(0);setQuery('');setPhase('');setStatus('');setCompare([])};
 const navigate=useCallback((to:string)=>{setRoute(to);location.hash=to;setMobile(false);setQuery('');setOffset(0);setPhase('');setStatus('')},[]);
 useEffect(()=>{const handler=()=>{const next=location.hash.slice(1);if(next==='workspace-main')return;setRoute(nav.some(n=>n[0]===next)?next:'overview')};window.addEventListener('hashchange',handler);return()=>window.removeEventListener('hashchange',handler)},[]);
 useEffect(()=>{let alive=true;Promise.all([api.datasets(),api.health()]).then(([ds,h])=>{if(alive){setDatasets(ds.items);setHealth(h);setDatasetId(id=>ds.items.some(d=>d.id===id)?id:(ds.items[0]?.id||'sample-fixture'))}}).catch(e=>{if(alive){setError(e.message);setLoading(false)}});return()=>{alive=false}},[refresh]);
 useEffect(()=>{let alive=true;setLoading(true);setError('');setCompare([]);setDetail(null);setSelected('');Promise.all([api.overview(datasetId),api.studies(datasetId,{limit:100})]).then(([o,s])=>{if(alive){setOverview(o);setAllRows(s.items);setLoading(false)}}).catch(e=>{if(alive){setError(e.message);setLoading(false)}});return()=>{alive=false}},[datasetId,refresh]);
 useEffect(()=>{let alive=true;const timeout=setTimeout(()=>api.studies(datasetId,{q:query,phase,status,sort_by:sort,offset,limit:25}).then(r=>{if(alive){setRows(r.items);setTotal(r.total)}}).catch(e=>{if(alive)setError(e.message)}),150);return()=>{alive=false;clearTimeout(timeout)}},[datasetId,query,phase,status,sort,offset,refresh]);
 useEffect(()=>{if(!toast)return;const t=setTimeout(()=>setToast(''),4500);return()=>clearTimeout(t)},[toast]);
 const openStudy=async(id:string)=>{setDetailBusy(true);setError('');try{const d=await api.detail(datasetId,id);setSelected(id);setAllRows(rows=>rows.some(r=>r.nct_id===id)?rows:[...rows,{...d.study,pci:d.pci.score,complexity:d.pci.category}]);setDetail(d)}catch(e){setError((e as Error).message)}finally{setDetailBusy(false)}};
 const closeDetail=useCallback(()=>setDetail(null),[]);const closeCompare=useCallback(()=>setShowCompare(false),[]);const closeSettings=useCallback(()=>setSettings(false),[]);
 const exportData=async(format:'csv'|'html')=>{try{await api.export(datasetId,format);setToast(format==='csv'?'Study CSV exported':'Report ready. Open the downloaded HTML and print to PDF.')}catch(e){setError((e as Error).message)}};
 const onImported=(d:Dataset)=>{setDatasets(ds=>[d,...ds.filter(x=>x.id!==d.id)]);switchDataset(d.id);setToast(`${d.row_count} records imported. Applying the active saved model.`);setAutoPredict(true);navigate('predict');setRefresh(n=>n+1)};
 useEffect(()=>{if(route==='overview')api.overview(datasetId).then(setOverview).catch(()=>{});},[route,datasetId]);
 useEffect(()=>{const changed=()=>api.overview(datasetId).then(setOverview).catch(()=>{});window.addEventListener('cti-models-changed',changed);return()=>window.removeEventListener('cti-models-changed',changed)},[datasetId]);
 const current=overview?.dataset||datasets.find(d=>d.id===datasetId);const title=titles[route]||titles.overview;
 const selectedStudy=allRows.find(row=>row.nct_id===selected)||rows.find(row=>row.nct_id===selected);
 const studyChoices=[...new Map([...allRows,...rows].map(row=>[row.nct_id,row])).values()];
 const animationProps={datasetId,nctId:selected||undefined,study:selectedStudy,rows:studyChoices,active:true};
 const toggleCompare=(id:string)=>{setCompare(a=>a.includes(id)?a.filter(x=>x!==id):a.length<3?[...a,id]:a);const picked=rows.find(r=>r.nct_id===id);if(picked)setAllRows(a=>a.some(r=>r.nct_id===id)?a:[...a,picked])};
 const restricted=(route==='experiments'&&!isOwner)||(route==='assistant'&&!canChat)||(['digital-twin','what-if'].includes(route)&&!canScenario)||(route==='roles'&&!canManage)||(route==='data'&&!canWrite);

 return <div className="app-shell v5202-shell"><a className="cti-skip-link" href="#workspace-main" onClick={e=>{e.preventDefault();document.getElementById('workspace-main')?.focus()}}>Skip to workspace</a><aside className={`sidebar ${mobile?'open':''}`} aria-label="Workspace navigation"><a className="brand" href="#overview" onClick={()=>navigate('overview')}><div><strong>Clinical Trial<br/>Intelligence</strong></div></a><nav aria-label="Main navigation">{visibleNav.filter(n=>coreRoutes.has(n[0])).map(([id,label,Icon])=><button key={id} className={route===id?'active':''} onClick={()=>navigate(id)} aria-current={route===id?'page':undefined}><Icon size={20}/><span>{label}</span></button>)}<div className="cti-nav-more"><button className={!coreRoutes.has(route)?'active':''} onClick={()=>setMoreOpen(v=>!v)} aria-expanded={moreOpen||!coreRoutes.has(route)}><Menu size={20}/><span>More tools</span><ChevronDown size={14}/></button>{(moreOpen||!coreRoutes.has(route))&&<div className="cti-nav-secondary">{visibleNav.filter(n=>!coreRoutes.has(n[0])).map(([id,label,Icon])=><button key={id} className={route===id?'active':''} onClick={()=>navigate(id)} aria-current={route===id?'page':undefined}><Icon size={17}/><span>{label}</span></button>)}</div>}</div></nav><div className="sidebar-bottom"><div className="workspace-version"><span>CTI WORKBENCH</span><span>v5.2.0.2</span></div><p><Info size={15}/>Research use only</p></div></aside>{mobile&&<button className="nav-overlay" aria-label="Close navigation" onClick={()=>setMobile(false)}/>}
 <div className="main-shell"><header className="topbar"><div className="breadcrumb"><button className="icon-btn mobile-menu" aria-label="Open navigation" onClick={()=>setMobile(v=>!v)}><Menu/></button><strong className="cti-breadcrumb-label">{nav.find(n=>n[0]===route)?.[1]||'Overview'}</strong></div><div className="topbar-right"><WorkspaceBar/><label className="dataset-picker"><Database size={15}/><select aria-label="Active dataset" value={datasetId} onChange={e=>switchDataset(e.target.value)}>{datasets.length?datasets.map(d=><option key={d.id} value={d.id}>{d.name}</option>):<option value="sample-fixture">Sample dataset</option>}</select><ChevronDown size={13}/></label><span className="avatar" title={user.name}>{user.name.split(" ").slice(0,2).map((s:string)=>s[0]).join("").toUpperCase()}</span></div></header>
 <main id="workspace-main" tabIndex={-1}>{route!=='overview'&&<div className={`page-heading ${route==='home'?'home-heading':''}`}><div><h1>{title}</h1></div><div className="heading-actions"><ExportButton onClick={()=>exportData('html')}/>{canWrite&&<button className="btn primary" onClick={()=>navigate('data')}><Upload size={16}/>Import dataset</button>}</div></div>}
 {DEMO?<Notice kind="sample">Interactive v5.2 preview · five interface fixtures plus separately labelled frozen real-model evidence. Live imports, prediction and AI run in the full project.</Notice>:current?.is_fixture?<Notice kind="sample">Sample workspace · {current.row_count} software-test records. No scientific results are implied.</Notice>:current?<div className={`source-strip ${route==='overview'?'cti-overview-source-strip':''}`}><CheckCircle2 size={15}/>{current.name}<span>·</span>{number(current.row_count)} imported records<span>·</span>Source preserved</div>:null}
 {error&&<Notice kind="error">{error} <button className="text-btn" onClick={()=>setRefresh(n=>n+1)}>Retry</button></Notice>}
 {loading?<div className="loading-state"><span className="spinner"/>Loading your research workspace…</div>:!overview?<Empty title="Connect to your workbench">Start the backend using the supplied launcher, then press Retry. <button className="btn secondary" onClick={()=>setRefresh(n=>n+1)}>Retry connection</button></Empty>:<>
 {route==='home'&&<ResearchHome dataset={overview.dataset} onNavigate={navigate}/>}
 {restricted&&<Notice>This tool is unavailable for your project role.</Notice>}
 {evidenceRoutes.has(route)&&!restricted&&<section className="cti-study-context"><label>Study<select aria-label="Selected study for visualization" value={selected} onChange={e=>setSelected(e.target.value)}><option value="">Choose a study</option>{studyChoices.map(study=><option key={study.nct_id} value={study.nct_id}>{study.nct_id} · {study.title}</option>)}</select></label><button className="text-btn" onClick={()=>navigate('explorer')}>Browse all studies</button>{selectedStudy&&<p>{nice(selectedStudy.phase)} · {nice(selectedStudy.status)} · {number(selectedStudy.enrollment)} participants</p>}</section>}
 {route==='sources'&&<ResearchSources key="search"/>}
 {route==='library'&&<ResearchSources key="saved" saved/>}
 {route==='predict'&&<PredictionStudio dataset={overview.dataset} autoPredict={autoPredict} onAutoDone={()=>setAutoPredict(false)} onNavigate={navigate} onScenario={(id,branch,study)=>{setSelected(id);setScenarioModel(branch);if(study)setAllRows(rows=>rows.some(row=>row.nct_id===id)?rows:[...rows,study]);else api.detail(datasetId,id).then(detail=>setAllRows(rows=>rows.some(row=>row.nct_id===id)?rows:[...rows,detail.study])).catch(e=>setError(e.message));navigate('what-if')}}/>}
 {route==='protocols'&&<ProtocolLab/>}
 {route==='models'&&<ModelRegistry/>}
 {route==='workspace'&&<><VerificationPanel/><PlatformSettings/></>}
 {route==='overview'&&<EnhancedOverview key={datasetId} dataset={overview.dataset} overview={overview} rows={rows} total={total} query={query} setQuery={setQuery} phase={phase} setPhase={setPhase} status={status} setStatus={setStatus} offset={offset} setOffset={setOffset} onSelect={openStudy} onNavigate={navigate} selected={compare} onCompare={toggleCompare} onShowCompare={()=>setShowCompare(true)} projectId={project.id}/>}
 {route==='explorer'&&<section className="panel"><header className="panel-heading"><h2>Studies <span className="count">{total}</span></h2><div className="inline-actions"><button className="btn secondary" disabled={compare.length<2} onClick={()=>setShowCompare(true)}>Compare {compare.length?`(${compare.length})`:''}</button><ExportButton label="Export CSV" onClick={()=>exportData('csv')}/></div></header><div className="explorer-filters"><SearchBox value={query} onChange={v=>{setQuery(v);setOffset(0)}}/><select aria-label="Filter phase" value={phase} onChange={e=>{setPhase(e.target.value);setOffset(0)}}><option value="">All phases</option>{Object.keys(overview.phase_counts).map(p=><option key={p} value={p}>{nice(p)}</option>)}</select><select aria-label="Filter status" value={status} onChange={e=>{setStatus(e.target.value);setOffset(0)}}><option value="">All statuses</option>{Object.keys(overview.status_counts).map(p=><option key={p} value={p}>{nice(p)}</option>)}</select><select aria-label="Sort studies" value={sort} onChange={e=>{setSort(e.target.value);setOffset(0)}}><option value="nct_id">Sort: Study ID</option><option value="enrollment">Sort: Enrollment</option><option value="title">Sort: Title</option></select></div><StudyTable rows={rows} onSelect={openStudy} selected={compare} onCompare={toggleCompare}/><footer className="table-footer"><span>Pick up to 3 studies to compare</span><div className="pagination"><span>{total?offset+1:0}–{Math.min(offset+25,total)} of {total}</span><button className="icon-btn" aria-label="Previous page" disabled={!offset} onClick={()=>setOffset(n=>Math.max(0,n-25))}><ChevronLeft size={17}/></button><button className="icon-btn" aria-label="Next page" disabled={offset+25>=total} onClick={()=>setOffset(n=>n+25)}><ChevronRight size={17}/></button></div></footer></section>}
 {route==='complexity'&&<Complexity rows={allRows} selected={selected}/>}
 {route==='data'&&canWrite&&<><DataManager datasets={datasets} current={datasetId} overview={overview} onSelect={switchDataset} onImported={onImported}/><AdditionalImports onImported={onImported}/></>}
 {route==='experiments'&&isOwner&&<Experiments dataset={overview.dataset} rows={allRows} onChanged={()=>window.dispatchEvent(new Event('cti-models-changed'))}/>}
 {route==='academy'&&<PhaseAcademy rows={allRows} onStudy={openStudy}/>}
 {route==='phase-model'&&<PhaseModels dataset={overview.dataset} rows={allRows} canTrain={isOwner}/>}
 {route==='assistant'&&canChat&&<Assistant key={overview.dataset.id} dataset={overview.dataset} rows={allRows} routing={health.assistant}/>}
 {route==='research-hub'&&<ResearchHub dataset={overview.dataset} rows={allRows} onStudy={openStudy} onNavigate={navigate}/>}
 {route==='digital-twin'&&canScenario&&<DigitalTwin dataset={overview.dataset} rows={allRows}/>}
 {route==='formula-studio'&&<FormulaStudio rows={allRows}/>}
 {route==='validation-lab'&&<ValidationLab dataset={overview.dataset}/>}
 {route==='ai-pipeline'&&<AnimatedPipeline {...animationProps}/>}
 {route==='trial-timeline'&&<TrialTimeline {...animationProps}/>}
 {route==='xai'&&<XAIAnimations {...animationProps}/>}
 {route==='recruitment'&&<RecruitmentJourney {...animationProps}/>}
 {route==='what-if'&&canScenario&&<WhatIfSimulator {...animationProps} modelName={scenarioModel}/>}
 {route==='fusion'&&<MultimodalFusion {...animationProps}/>}
 {route==='roles'&&canManage&&<RoleManager />}
 </>}
 <footer className="page-footer"><span><Activity size={13}/> Clinical Trial Intelligence Workbench</span><span>Protocol research · transparent methods · traceable evidence</span></footer></main></div>
 {toast&&<div className="toast" role="status"><CheckCircle2 size={18}/>{toast}<button className="icon-btn" aria-label="Dismiss notification" onClick={()=>setToast('')}><X size={15}/></button></div>}
 {detailBusy&&<div className="busy-indicator" role="status">Loading study…</div>}
 {detail&&<Modal title="Study details" onClose={closeDetail} wide><DetailBody detail={detail} onLab={()=>{setDetail(null);navigate('complexity')}}/></Modal>}
 {showCompare&&<Modal title="Compare studies" onClose={closeCompare} wide><div className="panel-padding"><div className="table-wrap"><table className="compare-table"><thead><tr><th>Protocol field</th>{compare.map(id=><th key={id}>{id}</th>)}</tr></thead><tbody>{['title','phase','status','enrollment','number_of_arms','primary_outcomes','secondary_outcomes','criteria_count','pci'].map(key=><tr key={key}><th>{nice(key)}</th>{compare.map(id=><td key={id}>{nice([...rows,...allRows].find(r=>r.nct_id===id)?.[key])}</td>)}</tr>)}</tbody></table></div><Notice>Comparison is descriptive. PCI differences are not evidence of different outcome probabilities.</Notice></div></Modal>}
 {settings&&<Modal title="Connection settings" onClose={closeSettings}><div className="panel-padding"><p className="muted">If you enabled API_BEARER_TOKEN on your local server, enter that access token here. This is not your AI provider key.</p><label>API access token<input type="password" value={token} onChange={e=>setToken(e.target.value)} autoComplete="off"/></label><p className="small muted">Kept only in this browser tab’s session storage. AI provider keys belong in the backend .env file.</p><div className="form-actions"><button className="btn secondary" onClick={()=>setToken('')}>Clear</button><button className="btn primary" onClick={()=>{if(token)sessionStorage.setItem('cti-api-token',token);else sessionStorage.removeItem('cti-api-token');setSettings(false);setRefresh(n=>n+1)}}>Save & reconnect</button></div></div></Modal>}
 </div>
}
