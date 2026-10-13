/** Known-answer checks against the shared scientific specification, executed without a browser. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from '../frontend/node_modules/typescript/lib/typescript.js';
const spec=JSON.parse(fs.readFileSync(new URL('../configs/formulas.json',import.meta.url),'utf8'));
const source=fs.readFileSync(new URL('../frontend/src/formulas.ts',import.meta.url),'utf8').replace("import specification from '../../configs/formulas.json';",`const specification=${JSON.stringify(spec)};`);
const compiled=ts.transpileModule(source,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}}).outputText;
const {pci,planning,metricExamples}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
for(const test of spec.parity_cases){const actual=pci(test.row);assert.equal(actual.score,test.expected.score,test.id);assert.equal(actual.category,test.expected.category,test.id);assert.deepEqual(actual.missing_fields,test.expected.missing_fields,test.id)}
assert.equal(pci({criteria_count:'1.'}).score,.63,'trailing decimal should be accepted');
for(const value of [Infinity,-Infinity,NaN,true,[],{},'0x10','1_000'])assert.equal(pci({criteria_count:value}).score,0,'invalid input');
for(const weights of [[1],[NaN,20,20,15,10,10],[-1,20,20,15,10,36],[1,1,1,1,1,1]])assert.throws(()=>pci({},weights),/weights/i);
assert.ok(Object.values(pci({criteria_count:'0.'+'9'.repeat(319)}).components).every(Number.isFinite),'long decimal contributions must be finite');
const p=planning(120,10,2,3,12);assert.equal(p.recruitment_months,6);assert.equal(p.total_months,21);
assert.throws(()=>planning(120,0,2,3,12));assert.throws(()=>planning(NaN,10,2,3,12));
assert.throws(()=>planning(240,1,1e-320,3,6),/finite/i);
const m=metricExamples();assert.equal(m.mae,1/3);assert.equal(m.rmse,Math.sqrt(1/3));assert.equal(m.r2,.5);assert.ok(Math.abs(m.brier-.04)<1e-12);assert.ok(Math.abs(m.cosine-1/Math.sqrt(2))<1e-12);
console.log(`${spec.parity_cases.length} shared PCI cases, invalid inputs, custom weights, planning and metric known answers passed.`);
