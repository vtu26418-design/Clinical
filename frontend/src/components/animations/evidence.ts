export const finite = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null;
export const formatNumber = (value: unknown, digits = 1) => finite(value)?.toLocaleString(undefined, {maximumFractionDigits: digits}) ?? 'Unknown';

export function durationEvidence(duration: any) {
  const days = duration?.status === 'available' && duration?.is_demo !== true ? finite(duration.duration_days) : null;
  return {days, available: days !== null, reason: duration?.reason || 'No compatible saved-model duration is available.'};
}

export function explanationEvidence(raw: any): {kind: 'local'|'global'|'constant'|'fusion'|'unavailable'; items: {name:string;value:number}[]; reason:string; units:string} {
  const units = raw?.units || 'model units';
  const empty = {kind:'unavailable' as const,items:[],units,reason:raw?.reason || raw?.note || 'No supported explanation is available for this saved model.'};
  if (!raw || raw.is_demo === true || raw.status === 'unavailable') return empty;
  if (raw.scope === 'constant' || /constant|median_baseline/i.test(raw.method || '')) return {kind:'constant',items:[],units,reason:raw.note || 'This baseline predicts the same duration for every compatible record. Feature effects are zero.'};
  if (Array.isArray(raw.components) && raw.components.length) return {kind:'fusion',items:raw.components.filter((c:any)=>finite(c.weight)!==null).map((c:any)=>({name:c.model_name,value:c.weight})),units:'fusion weight',reason:raw.note || ''};
  const global = /global/i.test(raw.scope || '') || /importance/i.test(raw.method || '');
  const key = global ? 'importance' : 'contribution';
  const items = (Array.isArray(raw.features) ? raw.features : []).filter((f:any)=>finite(f[key])!==null).map((f:any)=>({name:String(f.feature),value:f[key]}));
  if (!items.length) return empty;
  return {kind:global ? 'global' : 'local',items,units,reason:raw.note || ''};
}

export function predictedCompletion(start: string | null | undefined, precision: string | null | undefined, days: number | null) {
  if (precision !== 'day' || !start || !/^\d{4}-\d{2}-\d{2}$/.test(start) || finite(days) === null || days! < 0) return null;
  const date = new Date(`${start}T00:00:00Z`);
  if (!Number.isFinite(date.getTime()) || date.toISOString().slice(0,10) !== start) return null;
  date.setUTCDate(date.getUTCDate() + Math.round(days!));
  return date.toISOString().slice(0,10);
}

export const overrideFields = ['enrollment','number_of_arms','primary_outcomes','secondary_outcomes','criteria_count','text_complexity'] as const;
export function scenarioOverrides(values: Record<string,string>): Record<string,number> {
  const result:Record<string,number> = {};
  for (const field of overrideFields) {
    if (values[field] === undefined || values[field].trim() === '') continue;
    const number = Number(values[field]);
    if (!Number.isFinite(number) || number < 0) throw Error('Protocol overrides must be finite, non-negative numbers.');
    result[field] = number;
  }
  return result;
}

export function planningAssumptions(values: Record<string,string>) {
  const number = (field:string, positive:boolean) => {
    const value = values[field]?.trim() ? Number(values[field]) : NaN;
    if (!Number.isFinite(value) || (positive ? value <= 0 : value < 0)) throw Error(`Planning ${field.replaceAll('_',' ')} must be a ${positive?'positive':'non-negative'} number.`);
    return value;
  };
  const sites = number('sites',true);
  if (!Number.isInteger(sites)) throw Error('Planning sites must be a positive whole number.');
  return {sites,monthly_rate_per_site:number('monthly_rate_per_site',true),startup_months:number('startup_months',false),followup_months:number('followup_months',false)};
}


export function additiveWaterfall(raw:any, limit=8) {
  const evidence=explanationEvidence(raw),base=finite(raw?.intercept),sum=finite(raw?.sum_all_contributions);
  if(evidence.kind!=='local'||base===null||sum===null)return null;
  const features=evidence.items.slice(0,limit),shown=features.reduce((total,item)=>total+item.value,0);
  if(Math.abs(sum-shown)>1e-9)features.push({name:'Other model features',value:sum-shown});
  let current=base;
  const steps=[{name:'Baseline / intercept',from:0,to:base,value:base,total:true}];
  for(const feature of features){const from=current;current+=feature.value;steps.push({name:feature.name,from,to:current,value:feature.value,total:false})}
  steps.push({name:'Raw model output',from:0,to:base+sum,value:base+sum,total:true});
  return {steps,output:base+sum,units:evidence.units};
}
