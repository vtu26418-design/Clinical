import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import ts from 'typescript';

const path = new URL('./evidence.ts', import.meta.url);
async function subject() {
  let source;
  try { source = await readFile(path, 'utf8'); }
  catch { assert.fail('Selected-study evidence helpers are missing'); }
  const output = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
  return import(`data:text/javascript;base64,${Buffer.from(output).toString('base64')}`);
}

test('unavailable duration never becomes a numerical model prediction', async () => {
  const {durationEvidence} = await subject();
  assert.equal(durationEvidence({status:'unavailable', duration_days:720}).days, null);
  assert.equal(durationEvidence({status:'available', duration_days:0}).days, 0);
  assert.equal(durationEvidence({status:'available', duration_days:NaN}).days, null);
});

test('linear contributions retain their sign and global importance retains its scope', async () => {
  const {explanationEvidence} = await subject();
  const local = explanationEvidence({status:'available',method:'linear_contributions',scope:'local',units:'days',features:[{feature:'enrollment',contribution:-12},{feature:'arms',contribution:8}]});
  assert.equal(local.kind, 'local');
  assert.deepEqual(local.items.map(v=>v.value), [-12,8]);
  const global = explanationEvidence({status:'available',method:'tree_feature_importance',scope:'global',features:[{feature:'enrollment',importance:0.6}]});
  assert.equal(global.kind, 'global');
  assert.equal(global.items[0].value, 0.6);
});

test('demo attributions are rejected and constant baselines do not invent features', async () => {
  const {explanationEvidence} = await subject();
  assert.equal(explanationEvidence({status:'available',is_demo:true,features:[{feature:'x',contribution:30}]}).kind, 'unavailable');
  const constant = explanationEvidence({status:'available',method:'constant_baseline',scope:'local',features:[],base_value:14,predicted_value:14});
  assert.equal(constant.kind, 'constant');
  assert.deepEqual(constant.items, []);
});

test('partial registry dates preserve precision and never create an exact completion date', async () => {
  const {predictedCompletion} = await subject();
  assert.equal(predictedCompletion('2024-01', 'month', 30), null);
  assert.equal(predictedCompletion('2024-01-01', 'day', 30), '2024-01-31');
  assert.equal(predictedCompletion('2024-02-31', 'day', 30), null);
});

test('scenario overrides use supported source fields and explicit planning assumptions', async () => {
  const {scenarioOverrides,planningAssumptions} = await subject();
  assert.deepEqual(scenarioOverrides({enrollment:'100',number_of_arms:'2',primary_outcomes:'',criteria_count:'12'}), {enrollment:100,number_of_arms:2,criteria_count:12});
  assert.throws(()=>scenarioOverrides({enrollment:'-1'}), /non-negative/);
  assert.deepEqual(planningAssumptions({sites:'4',monthly_rate_per_site:'2.5',startup_months:'0',followup_months:'6'}), {sites:4,monthly_rate_per_site:2.5,startup_months:0,followup_months:6});
  assert.throws(()=>planningAssumptions({sites:'0',monthly_rate_per_site:'2',startup_months:'0',followup_months:'1'}), /positive/);
});


test('waterfall reconciles omitted features and preserves the actual raw output', async()=>{
 const {additiveWaterfall}=await subject();
 const result=additiveWaterfall({scope:'local',method:'linear contributions',intercept:100,sum_all_contributions:-20,features:[{feature:'observed',contribution:10}]});
 assert.equal(result.output,80);
 assert.equal(result.steps[2].value,-30);
 assert.equal(result.steps.at(-1).to,80);
 assert.equal(additiveWaterfall({scope:'global',method:'feature importance',features:[{feature:'x',importance:1}]}),null);
});
