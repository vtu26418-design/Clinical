import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm,readFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

async function subject(contents){
 const folder=await mkdtemp(join(tmpdir(),'cti-quality-test-'));
 try{
  const output=join(folder,'subject.mjs');
  await build({stdin:{contents,resolveDir:fileURLToPath(new URL('./',import.meta.url)),loader:'tsx'},bundle:true,platform:'node',format:'esm',outfile:output,loader:{'.css':'empty'},banner:{js:'import {createRequire} from "node:module";const require=createRequire(import.meta.url);'},define:{'import.meta.env':'{}'},logLevel:'silent'});
  return await import(pathToFileURL(output).href);
 }finally{await rm(folder,{recursive:true,force:true})}
}

test('quality transport preserves project authentication and explicit task/split',async()=>{
 const {fetchModelQuality}=await subject("export {fetchModelQuality} from './ModelQuality.tsx'");
 const previousFetch=globalThis.fetch,previousStorage=globalThis.sessionStorage;
 const requests=[];
 globalThis.sessionStorage={getItem:key=>key==='cti-project-id'?'project-reader-scope':key==='cti-api-token'?'software-token':null};
 globalThis.fetch=async(url,options)=>{requests.push({url,options});return new Response(JSON.stringify({selected:{n:3}}),{headers:{'Content-Type':'application/json'}})};
 try{
  const report=await fetchModelQuality('phase','validation');
  assert.equal(report.selected.n,3);
  const request=requests[0],url=new URL(request.url,'http://local');
  assert.equal(url.pathname,'/api/v1/model-quality');
  assert.equal(url.searchParams.get('task'),'phase');
  assert.equal(url.searchParams.get('split'),'validation');
  assert.equal(request.options.headers.get('X-Project-ID'),'project-reader-scope');
  assert.equal(request.options.headers.get('Authorization'),'Bearer software-token');
  assert.equal(request.options.credentials,'include');
 }finally{globalThis.fetch=previousFetch;globalThis.sessionStorage=previousStorage}
});

test('metric cards name AUROC distinctly and regression stays in days',async()=>{
 const {html}=await subject(`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {QualityMetrics} from './ModelQuality.tsx';export const html=renderToStaticMarkup(<QualityMetrics task="duration" row={{model_name:'model',split:'test',split_role:'test',n:3,regression:{mae_days:12,rmse_days:18,median_absolute_error_days:10,r2:-.2},classification:{auroc:.73,average_precision:.6,brier:.2,log_loss:.5}}}/>);`);
 assert.match(html,/AUROC/);assert.match(html,/12.*days/);assert.match(html,/Median absolute error/);
 assert.doesNotMatch(html,/73%|regression accuracy|90% accuracy/i);
});

test('phase confusion matrix displays actual and predicted counts with labels',async()=>{
 const {html}=await subject(`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {QualityConfusion} from './ModelQuality.tsx';export const html=renderToStaticMarkup(<QualityConfusion classification={{labels:['PHASE1','PHASE2'],confusion_matrix:[[5,2],[1,4]],per_class:[{label:'PHASE1',support:7},{label:'PHASE2',support:5}]}}/>);`);
 assert.match(html,/Actual.*predicted/s);assert.match(html,/PHASE1/);assert.match(html,/>5</);assert.match(html,/>2</);
});

test('recorded confidence intervals show bounds and resampling support',async()=>{
 const {html}=await subject(`import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {QualityIntervals} from './ModelQuality.tsx';export const html=renderToStaticMarkup(<QualityIntervals intervals={{status:'recorded_not_recomputed',reason:'Recorded, not independently recomputed.',recorded:{method:'paired trial bootstrap percentile',level:.95,mae:{lower:9,upper:11,valid_resamples:200}}}}/>);`);
 assert.match(html,/Recorded bootstrap confidence intervals/);assert.match(html,/95%/);assert.match(html,/>9</);assert.match(html,/>11</);assert.match(html,/>200</);assert.match(html,/not independently recomputed/);
});

test('Settings and Validation Lab both expose the shared view without requiring experiments',async()=>{
 const settings=await readFile(new URL('../v5/PlatformSettings.tsx',import.meta.url),'utf8');
 const validation=await readFile(new URL('../components/ValidationLab.tsx',import.meta.url),'utf8');
 assert.match(settings,/Model quality/);assert.match(settings,/<ModelQuality/);
 assert.ok(validation.indexOf('<ModelQuality')>=0);
 assert.ok(validation.indexOf('<ModelQuality')<validation.indexOf('Follow a record through validation'));
});
