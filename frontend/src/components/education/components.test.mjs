import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
async function render(file,name,props={}) {
 const folder=await mkdtemp(join(tmpdir(),'cti-education-ui-'));
 try{
  const output=join(folder,'render.mjs'),source=fileURLToPath(new URL(file,import.meta.url));
  await build({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {${name}} from ${JSON.stringify(source)};export const html=renderToStaticMarkup(React.createElement(${name},{...${JSON.stringify(props)},onNavigate:()=>{},onStudy:()=>{}}));`,resolveDir:fileURLToPath(new URL('../../../',import.meta.url)),loader:'tsx'},bundle:true,platform:'node',format:'esm',outfile:output,banner:{js:'import {createRequire} from "node:module"; const require=createRequire(import.meta.url);'},define:{'import.meta.env':'{}'},plugins:[{name:'ignore-css',setup(b){b.onLoad({filter:/\.css$/},()=>({contents:'',loader:'js'}))}}],logLevel:'silent'});
  return (await import(pathToFileURL(output).href)).html;
 }finally{await rm(folder,{recursive:true,force:true})}
}
test('Academy keeps optional Phase 0, all stages, original quiz and readable no-data fallback',async()=>{
 const html=await render('../PhaseAcademy.tsx','PhaseAcademy',{rows:[]});
 for(const label of ['Phase 0','Phase I','Phase II','Phase III','Phase IV','Optional','Participants','Study design','Observations','Review'])assert.ok(html.includes(label),label);
 assert.match(html,/Which stage most directly focuses on dose and tolerability/);
 assert.match(html,/No matching record in this workspace/);
 assert.match(html,/Participant symbols are illustrative/);
 assert.match(html,/fda.gov\/patients\/drug-development-process/);
 assert.match(html,/cancer.gov/);
 assert.equal((html.match(/class="cti-scene-panel /g)||[]).length,1);
});
test('Home renders one guided scene, readable workflow actions, original navigation and real scoped count',async()=>{
 const html=await render('../../v52/ResearchHome.tsx','ResearchHome',{dataset:{id:'empty',name:'Empty imported cohort',row_count:0,is_fixture:false}});
 assert.match(html,/Walk through the research journey/);
 assert.match(html,/Import and validate records/);
 for(const action of ['Import','Review','Predict','Interpret','Compare','Find source evidence','Predict trial duration','Compare a scenario'])assert.ok(html.includes(action),action);
 assert.match(html,/0 imported records selected/);
 assert.match(html,/Decorative · no genomic inputs/);
 assert.match(html,/Explore the virtual clinic/);
 assert.equal((html.match(/class="cti-scene-panel /g)||[]).length,1);
});
test('Helix remains decorative with accessible 2D rotation and no automatic generated scientific values',async()=>{
 const html=await render('../animations/MolecularAnimation.tsx','MolecularAnimation',{scene3D:true});
 assert.match(html,/no genomic inputs/i);assert.match(html,/biological simulation/);assert.match(html,/Helix rotation/);assert.match(html,/Reset orientation/);
 assert.doesNotMatch(html,/cti-scene-values/);
 assert.match(html,/aria-valuetext="0 degrees"/);
});
test('Academy matching uses only the recorded phase and missing enrollment stays unknown',async()=>{
 const html=await render('../PhaseAcademy.tsx','PhaseAcademy',{rows:[{nct_id:'NCT-SOURCE-UNKNOWN',title:'Missing phase record',phase:null,enrollment:42},{nct_id:'NCT-SOURCE-I',title:'Recorded Phase I',phase:'PHASE1',enrollment:null}]});
 assert.doesNotMatch(html,/NCT-SOURCE-UNKNOWN/);
 assert.match(html,/NCT-SOURCE-I/);
 assert.match(html,/Enrollment: —/);
 assert.doesNotMatch(html,/Enrollment: 0/);
});
