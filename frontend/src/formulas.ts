import specification from '../../configs/formulas.json';
import type {Study} from './types';

export const formulaSpec=specification;
export const pciParts=specification.fixed_reference_pci.components.map(c=>[c.label,c.key,c.ceiling,c.weight] as const);
type Fraction={n:bigint;d:bigint};
function decimal(value:unknown):Fraction|null{
 if((typeof value!=='number'&&typeof value!=='string')||String(value).trim()===''||!Number.isFinite(Number(value)))return null;
 const text=String(value).trim();const match=text.match(/^([+-]?)(\d+(?:\.\d*)?|\.\d+)(?:e([+-]?\d+))?$/i);if(!match)return null;
 const pieces=match[2].split('.');const digits=(pieces[0]||'0')+(pieces[1]||'');const exponent=Number(match[3]||0)-(pieces[1]?.length||0);
 // Avoid constructing huge integers for adversarial browser inputs.
 if(Math.abs(exponent)>specification.fixed_reference_pci.input_policy.max_absolute_decimal_scale||digits.length>specification.fixed_reference_pci.input_policy.max_decimal_digits)return null;
 const sign=match[1]==='-'?-1n:1n;
 return exponent>=0?{n:sign*BigInt(digits)*10n**BigInt(exponent),d:1n}:{n:sign*BigInt(digits),d:10n**BigInt(-exponent)};
}
function add(a:Fraction,b:Fraction):Fraction{return{n:a.n*b.d+b.n*a.d,d:a.d*b.d}}
function component(value:unknown,ceiling:number,weight:number):Fraction{
 const x=decimal(value),cap=decimal(ceiling)!,w=decimal(weight);
 if(!x||!w||x.n<0n)return{n:0n,d:1n};
 if(x.n*cap.d>=cap.n*x.d)return w;
 return{n:x.n*cap.d*w.n,d:x.d*cap.n*w.d};
}
function halfUp(f:Fraction,digits=specification.fixed_reference_pci.rounding.digits){const scale=10n**BigInt(digits);return Number((f.n*scale*2n+f.d)/(2n*f.d))/Number(scale)}
export function pci(row:Study|Record<string,unknown>,weights?:number[]){
 const rules=specification.fixed_reference_pci.custom_weights;
 if(weights&&(weights.length!==rules.count||weights.some(w=>!Number.isFinite(w)||w<rules.minimum||w>rules.maximum)||Math.abs(weights.reduce((s,w)=>s+w,0)-rules.sum)>rules.sum_tolerance))throw Error('Custom weights must be six finite values from 0 to 100, totaling 100.');
 const terms=pciParts.map(([label,key,ceiling,weight],i)=>({label,key,f:component(row[key],ceiling,weights?.[i]??weight)}));
 const total=terms.reduce((s,t)=>add(s,t.f),{n:0n,d:1n});const score=halfUp(total);
 const components=Object.fromEntries(terms.map(t=>[t.label,Number(t.f.n*1000000000000000n/t.f.d)/1000000000000000]));
 const missing_fields=terms.filter(t=>decimal(row[t.key])===null).map(t=>t.key);
 const category=specification.fixed_reference_pci.categories.find(c=>score<c.upper||(c.upper_inclusive&&score===c.upper))!.label;
 return{score,category,components,missing_fields,formula_id:weights?'custom_exploratory_pci':specification.fixed_reference_pci.id,
 methodology:weights?`${rules.scope}. Missing or invalid values contribute zero; categories use the same exploratory cutoffs. No clinical validity is established.`:specification.fixed_reference_pci.methodology};
}
export function planning(target:number,sites:number,rate:number,startup:number,followup:number){
 if(![target,sites,rate,startup,followup].every(Number.isFinite)||target<0||sites<=0||rate<=0||startup<0||followup<0)throw Error('Use finite nonnegative durations and enrollment, with positive sites and monthly rate.');
 const capacity=sites*rate,recruitment_months=target/capacity,total_months=startup+recruitment_months+followup;
 if(capacity<=0||![capacity,recruitment_months,total_months].every(Number.isFinite))throw Error('Planning arithmetic must produce finite durations; revise the site rate and target.');
 return{target_enrollment:target,sites,monthly_rate_per_site:rate,startup_months:startup,followup_months:followup,recruitment_months,total_months,
 formula:'recruitment_months = target_enrollment / (sites × monthly_rate_per_site); total_months = startup_months + recruitment_months + followup_months',
 assumptions:['Constant recruitment rate at every site; all sites start together.','Stages run sequentially; no dropouts, pauses, overlap or ramp-up included.','User-entered planning assumptions, not a fitted recruitment or duration forecast.']};
}
export function metricExamples(){
 const actual=[1,2,3],predicted=[1,2,4],errors=actual.map((v,i)=>v-predicted[i]),mean=actual.reduce((s,v)=>s+v,0)/actual.length;
 return{actual,predicted,mae:errors.reduce((s,v)=>s+Math.abs(v),0)/3,rmse:Math.sqrt(errors.reduce((s,v)=>s+v*v,0)/3),r2:1-errors.reduce((s,v)=>s+v*v,0)/actual.reduce((s,v)=>s+(v-mean)**2,0),brier:((.2-0)**2+(.8-1)**2)/2,cosine:(1*1+0*1)/(Math.sqrt(1)*Math.sqrt(2))};
}
