import type {Dataset} from '../types';

export function preferredDataset(datasets:Pick<Dataset,'id'|'is_fixture'>[],requested:string){
 return datasets.find(dataset=>dataset.id===requested)?.id||datasets.find(dataset=>dataset.id==='registry-v5205'&&!dataset.is_fixture)?.id||datasets.find(dataset=>!dataset.is_fixture)?.id||datasets[0]?.id||'';
}

/** The registered source is immutable; active-model results on detail are ignored. */
export function savedPredictionWorkspace(dataset:Pick<Dataset,'id'|'sha256'>,batch:any,item:any,detail:any){
 if(dataset.id!==batch.dataset?.id||!dataset.sha256||dataset.sha256!==batch.dataset?.sha256||detail.study?.nct_id!==item.nct_id){
  throw new Error('The saved prediction source does not match this record. Select its original dataset to review the evidence.');
 }
 const notRequested={status:'unavailable',reason:'This task was not requested in the saved prediction run.'};
 return {study:detail.study,pci:detail.pci,
  duration:batch.model?.task==='duration'?item.prediction:notRequested,
  phase:batch.model?.task==='phase'?item.prediction:notRequested,
  provenance:{dataset_id:batch.dataset.id,source_sha256:batch.dataset.sha256,prediction_run_id:batch.id,created_at:batch.created_at,model:batch.model}};
}
