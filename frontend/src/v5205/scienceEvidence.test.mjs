import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
async function subject(){const dir=await mkdtemp(join(tmpdir(),'cti-science-evidence-'));try{const out=join(dir,'subject.mjs');await build({entryPoints:[fileURLToPath(new URL('./scienceEvidence.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',outfile:out,logLevel:'silent'});return await import(pathToFileURL(out).href)}finally{await rm(dir,{recursive:true,force:true})}}
test('science evidence keeps exact source and model values and labels dataset counts',async()=>{
 const {scienceEvidence}=await subject();const dataset={id:'real',name:'Source',row_count:101135,source:'Registry',sha256:'abc',is_fixture:false};
 const study={nct_id:'NCT12345678',title:'Brain study',phase:'PHASE2',status:'COMPLETED',start_date:'2020-01',completion_date:null};
 const result=scienceEvidence(dataset,study,{study,pci:{score:0,category:'Low'},prediction:{status:'available',duration_days:789.123456,probability:0,model_name:'actual-branch',approved_model_id:'actual-model',run_id:'frozen',prediction_scope:'Retrospective research'}});
 assert.match(result.notes,/789\.123456/);assert.match(result.notes,/probability: 0/);assert.match(result.notes,/PCI score: 0/);assert.match(result.notes,/2020-01/);assert.match(result.notes,/Completion date as reported: Not reported/);assert.match(result.notes,/actual-branch/);
 const other=scienceEvidence(dataset,{...study,nct_id:'OTHER'},{study,pci:{score:9},prediction:{status:'available',duration_days:999}});
 assert.doesNotMatch(other.notes,/999|PCI score: 9/);
 const aggregate=scienceEvidence(dataset);assert.match(aggregate.notes,/Context: dataset/);assert.match(aggregate.notes,/not the number used to fit/);assert.doesNotMatch(aggregate.notes,/Predicted total duration/);
});
