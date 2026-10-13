import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

async function render(name,props={datasetId:'dataset-real'}) {
 const root=fileURLToPath(new URL('./',import.meta.url));
 const folder=await mkdtemp(join(tmpdir(),'cti-animation-test-'));
 try {
  const output=join(folder,'render.mjs');
  await build({stdin:{contents:`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {${name}} from ${JSON.stringify(root+name+'.tsx')}; export const html=renderToStaticMarkup(React.createElement(${name},${JSON.stringify(props)}));`,resolveDir:fileURLToPath(new URL('../../../',import.meta.url)),loader:'tsx'},bundle:true,platform:'node',format:'esm',outfile:output,banner:{js:'import {createRequire} from "node:module"; const require=createRequire(import.meta.url);'},define:{'import.meta.env':'{}'},plugins:[{name:'ignore-css',setup(b){b.onLoad({filter:/\.css$/},()=>({contents:'',loader:'js'}))}}],logLevel:'silent'});
  return (await import(pathToFileURL(output).href)).html;
 } finally {await rm(folder,{recursive:true,force:true})}
}
for(const name of ['AnimatedPipeline','TrialTimeline','XAIAnimations','RecruitmentJourney','WhatIfSimulator','MultimodalFusion']) {
 test(`${name} has no scientific output without a selected study`, async()=>{
  const html=await render(name);
  assert.match(html,/Select a study/);
  assert.doesNotMatch(html,/26\.4|1850|NCT04982120|0\.89|74%/);
 });
}
