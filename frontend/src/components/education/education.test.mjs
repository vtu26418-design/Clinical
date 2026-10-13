import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm,access} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
async function subject(){
 const path=fileURLToPath(new URL('./education.ts',import.meta.url));
 try{await access(path)}catch{assert.fail('The phase/journey scene adapter is missing')}
 const folder=await mkdtemp(join(tmpdir(),'cti-education-'));
 try{const output=join(folder,'subject.mjs');await build({entryPoints:[path],bundle:true,platform:'node',format:'esm',outfile:output,logLevel:'silent'});return await import(pathToFileURL(output).href)}finally{await rm(folder,{recursive:true,force:true})}
}
test('all five phase scenes keep the four original lesson steps and no invented values',async()=>{
 const {phaseScene,lessons}=await subject();
 for(let index=0;index<5;index++){const scene=phaseScene(index);assert.equal(scene.phaseIndex,index);assert.equal(scene.steps.length,4);assert.deepEqual(scene.steps.map(s=>s.detail),lessons[index].steps);assert.deepEqual(scene.values,[]);assert.equal(scene.mode,'conceptual');assert.match(scene.subtitle,/symbols.*illustrative/i)}
});
test('missing or out-of-range phase selections remain unknown instead of selecting Phase 0',async()=>{
 const {phaseScene}=await subject();for(const value of [null,undefined,-1,5,NaN,Infinity,1.5])assert.equal(phaseScene(value),null);
});
test('motion adapter never plays when either app or system reduction stops shared motion',async()=>{
 const {educationPlayback}=await subject();assert.equal(educationPlayback(true,{running:true,reduced:false}),true);assert.equal(educationPlayback(false,{running:true,reduced:false}),false);assert.equal(educationPlayback(true,{running:false,reduced:false}),false);assert.equal(educationPlayback(true,{running:true,reduced:true}),false);
});
test('research journey links each actual workflow action to its existing route',async()=>{
 const {RESEARCH_JOURNEY}=await subject();assert.deepEqual(RESEARCH_JOURNEY.map(s=>s.title),['Import','Review','Predict','Interpret','Compare']);assert.deepEqual(RESEARCH_JOURNEY.map(s=>s.route),['data','explorer','predict','xai','digital-twin']);assert.ok(RESEARCH_JOURNEY.every(s=>s.detail&&s.action));assert.match(RESEARCH_JOURNEY[2].detail,/saved model/i);assert.match(RESEARCH_JOURNEY[3].detail,/uncertainty/i);
});
