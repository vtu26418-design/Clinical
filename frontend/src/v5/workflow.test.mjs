import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
async function subject(){const dir=await mkdtemp(join(tmpdir(),'cti-workflow-'));try{const out=join(dir,'subject.mjs');await build({entryPoints:[fileURLToPath(new URL('./workflow.ts',import.meta.url))],bundle:true,platform:'node',format:'esm',outfile:out,logLevel:'silent'});return await import(pathToFileURL(out).href)}finally{await rm(dir,{recursive:true,force:true})}}

test('dataset selection prefers genuine records while preserving explicit fixture diagnostics',async()=>{
 const {preferredDataset}=await subject();const rows=[{id:'sample-fixture',is_fixture:true},{id:'real',is_fixture:false}];
 assert.equal(preferredDataset(rows,''),'real');assert.equal(preferredDataset(rows,'missing'),'real');
 assert.equal(preferredDataset(rows,'sample-fixture'),'sample-fixture');assert.equal(preferredDataset([],''),'');
 const reference={id:'registry-v5205',is_fixture:false};
 assert.equal(preferredDataset([...rows,reference],''),'registry-v5205');
 assert.equal(preferredDataset([...rows,reference],'real'),'real');
 assert.equal(preferredDataset([...rows,reference],'sample-fixture'),'sample-fixture');
});
test('saved result visualization uses exact batch prediction and rejects changed source identity',async()=>{
 const {savedPredictionWorkspace}=await subject();const dataset={id:'real',sha256:'frozen-source'};
 const pred={status:'available',duration_days:123,model_name:'saved-branch'};
 const batch={id:'batch1',dataset,model:{id:'old-model',task:'duration'},created_at:'2026-01-01',items:[]};
 const detail={study:{nct_id:'TRIAL1',title:'Source'},pci:{score:5},prediction:{status:'available',duration_days:999,model_name:'fresh-active'}};
 const packet=savedPredictionWorkspace(dataset,batch,{nct_id:'TRIAL1',prediction:pred},detail);
 assert.equal(packet.duration,pred);assert.equal(packet.phase.status,'unavailable');assert.equal(packet.provenance.model.id,'old-model');assert.equal(packet.study,detail.study);
 assert.throws(()=>savedPredictionWorkspace({...dataset,sha256:'changed'},batch,{nct_id:'TRIAL1',prediction:pred},detail),/source/i);
 assert.throws(()=>savedPredictionWorkspace(dataset,batch,{nct_id:'TRIAL2',prediction:pred},detail),/source/i);
});
