import {useEffect,useMemo,useState} from 'react';
import {api} from '../api';
import type {Dataset,Detail,Study} from '../types';
import {ScienceStudio} from './science/ScienceStudio';
import {scienceEvidence} from './scienceEvidence';

export function ContextScienceStudio({projectId,dataset,study,canEdit}:{projectId:string;dataset:Dataset;study?:Study;canEdit:boolean}){
 const [revision,setRevision]=useState(0);
 const [state,setState]=useState<{key:string;detail:Detail|null;error:string;loading:boolean}>({key:'',detail:null,error:'',loading:false});
 const scope=`${projectId}/${dataset.id}/${dataset.sha256||''}/${study?.nct_id||''}/${revision}`;
 useEffect(()=>{const changed=()=>setRevision(n=>n+1);window.addEventListener('cti-models-changed',changed);return()=>window.removeEventListener('cti-models-changed',changed)},[]);
 useEffect(()=>{let alive=true;if(!study){setState({key:scope,detail:null,error:'',loading:false});return}
  setState({key:scope,detail:null,error:'',loading:true});
  api.detail(dataset.id,study.nct_id).then(detail=>{if(alive)setState({key:scope,detail,error:'',loading:false})}).catch(error=>{if(alive)setState({key:scope,detail:null,error:error instanceof Error?error.message:'Study evidence is unavailable.',loading:false})});
  return()=>{alive=false};
 },[scope]);
 const detail=state.key===scope?state.detail:null;
 const evidence=useMemo(()=>scienceEvidence(dataset,study,detail),[dataset,study,detail]);
 return <>{state.key===scope&&state.loading&&<p role="status" className="small muted">Loading selected-study model evidence…</p>}
  {state.key===scope&&state.error&&<p role="alert" className="small muted">{state.error}</p>}
  <ScienceStudio scopeKey={scope} canEdit={canEdit} evidence={evidence}/></>;
}
