import test from 'node:test';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {mkdtemp,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

async function subject(contents){
 const folder=await mkdtemp(join(tmpdir(),'cti-search-test-'));
 try{
  const output=join(folder,'subject.mjs');
  await build({stdin:{contents,resolveDir:fileURLToPath(new URL('../',import.meta.url)),loader:'tsx'},bundle:true,platform:'node',format:'esm',outfile:output,banner:{js:'import {createRequire} from "node:module"; const require=createRequire(import.meta.url);'},define:{'import.meta.env':'{}'},logLevel:'silent'});
  return await import(pathToFileURL(output).href);
 }finally{await rm(folder,{recursive:true,force:true})}
}

test('training API defaults old callers to basic and sends an explicit expanded choice',async()=>{
 const {api}=await subject("export {api} from './api.ts'");
 const previousFetch=globalThis.fetch,previousStorage=globalThis.sessionStorage;
 const requests=[];
 globalThis.sessionStorage={getItem:()=>null};
 globalThis.fetch=async(url,options)=>{requests.push({url,body:JSON.parse(options.body)});return new Response(JSON.stringify({id:'candidate-run'}),{status:202,headers:{'Content-Type':'application/json'}})};
 try{
  await api.train('cohort');
  await api.train('cohort',true);
  await api.train('cohort',true,'expanded');
  await api.train('cohort',true,'expanded',true);
  assert.deepEqual(requests.map(request=>request.body),[
   {dataset_id:'cohort',enable_catboost:false,catboost_search:'basic'},
   {dataset_id:'cohort',enable_catboost:true,catboost_search:'basic'},
   {dataset_id:'cohort',enable_catboost:true,catboost_search:'expanded'},
   {dataset_id:'cohort',enable_catboost:true,catboost_search:'expanded',enable_accuracy_models:true}]);
  assert.ok(requests.every(request=>request.url==='/api/v1/experiments'));
 }finally{globalThis.fetch=previousFetch;globalThis.sessionStorage=previousStorage}
});

test('experiment controls label the optional searches, their relative fitting cost and uncertain benefit',async()=>{
 const {html}=await subject("import React from 'react';import {renderToStaticMarkup} from 'react-dom/server';import {Experiments} from './components/Experiments.tsx';export const html=renderToStaticMarkup(<Experiments dataset={{id:'cohort',name:'Software test',row_count:80,source:'fixture',is_fixture:true}} rows={[]} onChanged={()=>{}}/>);");
 assert.match(html,/Include CatBoost/);
 assert.match(html,/<option value="basic" selected="">Standard search<\/option>/);
 assert.match(html,/<option value="expanded">Expanded CatBoost search<\/option>/);
 assert.match(html,/2 configurations per task/);
 assert.match(html,/8 configurations per task/);
 assert.match(html,/more fitting time/);
 assert.match(html,/does not guarantee better/);
});

test('readiness sends requested options and validation errors show actionable messages without echoed inputs',async()=>{
 const {api}=await subject("export {api} from './api.ts'");
 const previousFetch=globalThis.fetch,previousStorage=globalThis.sessionStorage;globalThis.sessionStorage={getItem:()=>null};
 const urls=[];globalThis.fetch=async(url)=>{urls.push(url);return new Response(JSON.stringify({detail:{message:'Dataset validation failed.',errors:[{row:2,field:'completion_date',message:'Completion precedes start date.',input:'private-input-value'}]}}),{status:422,headers:{'Content-Type':'application/json'}})};
 try{
  await assert.rejects(api.readiness('cohort',{enable_catboost:true,enable_accuracy_models:true,catboost_search:'expanded'}),error=>error.message.includes('Completion precedes start date.')&&!error.message.includes('private-input-value')&&!error.message.startsWith('{'));
  const url=new URL(urls[0],'http://local');assert.equal(url.searchParams.get('enable_catboost'),'true');assert.equal(url.searchParams.get('catboost_search'),'expanded');
 }finally{globalThis.fetch=previousFetch;globalThis.sessionStorage=previousStorage}
});

test('design choices and objective are sent faithfully to readiness and duration and phase training',async()=>{
 const {api}=await subject("export {api} from './api.ts'");
 const previousFetch=globalThis.fetch,previousStorage=globalThis.sessionStorage,requests=[];
 globalThis.sessionStorage={getItem:()=>null};
 globalThis.fetch=async(url,options={})=>{requests.push({url,body:options.body?JSON.parse(options.body):null});return new Response('{}',{status:200,headers:{'Content-Type':'application/json'}})};
 const options={enable_design_models:true,enable_design_catboost:false,duration_selection_metric:'mae'};
 try{
  await api.readiness('cohort',options);await api.train('cohort',false,'basic',false,options);
  await api.phaseTrain('cohort',{enable_design_models:true,enable_design_catboost:false});
  const query=new URL(requests[0].url,'http://local').searchParams;
  for(const [key,value] of Object.entries(options))assert.equal(query.get(key),String(value));
  assert.deepEqual(requests[1].body,{dataset_id:'cohort',enable_catboost:false,catboost_search:'basic',...options});
  assert.deepEqual(requests[2].body,{dataset_id:'cohort',enable_design_models:true,enable_design_catboost:false});
 }finally{globalThis.fetch=previousFetch;globalThis.sessionStorage=previousStorage}
});
