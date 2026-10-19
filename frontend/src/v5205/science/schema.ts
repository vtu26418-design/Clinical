import {SCENES, type ScienceDocument,type DraftOrigin} from './types';

function record(value:unknown, keys:string[], path:string):Record<string,unknown>{
 if(!value||typeof value!=='object'||Array.isArray(value)||(Object.getPrototypeOf(value)!==Object.prototype&&Object.getPrototypeOf(value)!==null))throw Error(`${path} must be an object.`);
 const obj=value as Record<string,unknown>;
 if(Object.keys(obj).some(key=>!keys.includes(key))||keys.some(key=>!Object.hasOwn(obj,key)))throw Error(`${path} has missing or unsupported fields.`);
 return obj;
}
function text(value:unknown,min:number,max:number,path:string){if(typeof value!=='string'||value.length<min||value.length>max||(min>0&&!value.trim()))throw Error(`${path} must contain ${min}–${max} characters.`)}
function choice(value:unknown,choices:readonly unknown[],path:string){if(!choices.includes(value))throw Error(`${path} is unsupported.`)}
/** Accept declarative data only. Strings are literal text and never HTML, code or URLs to load. */
export function parseScienceDocument(input:unknown):ScienceDocument {
 const doc=record(input,['version','title','source_notes','scene','steps','settings'],'Storyboard');
 choice(doc.version,[1],'Version');text(doc.title,1,160,'Title');text(doc.source_notes,0,32000,'Source notes');choice(doc.scene,SCENES,'Scene');
 if(!Array.isArray(doc.steps)||doc.steps.length<1||doc.steps.length>12)throw Error('Use 1–12 explanation steps.');
 const ids=new Set<string>();
 doc.steps.forEach((value,index)=>{
  const step=record(value,['id','title','caption','narration','focus','labels'],`Step ${index+1}`);
  if(typeof step.id!=='string'||!/^[-_a-zA-Z0-9]{1,64}$/.test(step.id)||ids.has(step.id))throw Error('Step IDs must be unique letters, digits, hyphens or underscores (1–64).');ids.add(step.id);
  text(step.title,1,120,'Step title');text(step.caption,1,1400,'Caption');text(step.narration,0,2400,'Narration');choice(step.focus,['overview','input','transfer','processing','output'],'Focus');
  if(!Array.isArray(step.labels)||step.labels.length>8)throw Error('Use at most eight labels per step.');step.labels.forEach(value=>text(value,1,60,'Label'));
 });
 const settings=record(doc.settings,['accent','background','detail','speed','show_labels','camera','voice_uri','voice_rate'],'Settings');
 if(typeof settings.accent!=='string'||!/^#[a-fA-F0-9]{6}$/.test(settings.accent))throw Error('Accent must be a six-digit hex color.');
 choice(settings.background,['midnight','light'],'Background');choice(settings.detail,['low','standard'],'Detail');choice(settings.speed,[0.5,1,1.5,2],'Speed');choice(settings.camera,['orbit','front','close'],'Camera');
 if(typeof settings.show_labels!=='boolean')throw Error('Label visibility must be true or false.');text(settings.voice_uri,0,512,'Voice');
 if(typeof settings.voice_rate!=='number'||!Number.isFinite(settings.voice_rate)||settings.voice_rate<0.6||settings.voice_rate>1.4)throw Error('Voice rate must be between 0.6 and 1.4.');
 return structuredClone(doc) as unknown as ScienceDocument;
}
export function parseScienceImport(source:string){if(source.length>90000)throw Error('Storyboard file exceeds the 90 KB limit.');return parseScienceDocument(JSON.parse(source))}
export function parseScienceOrigin(value:unknown):DraftOrigin|null {
 if(value===null||value===undefined)return null;
 if(typeof value!=='object'||Array.isArray(value)||Object.getPrototypeOf(value)!==Object.prototype)throw Error('Origin must be a plain object.');
 const origin=value as Record<string,unknown>,allowed=['provider','model','generated','draft_id','source_sha256','needs_review','edited','verification'];
 if(Object.keys(origin).some(key=>!allowed.includes(key)))throw Error('Origin has unsupported fields.');
 text(origin.provider,1,120,'Origin provider');text(origin.model,1,200,'Origin model');if(origin.generated!==true)throw Error('Origin generated flag must be true.');
 if(origin.draft_id!==undefined&&origin.draft_id!==null&&(typeof origin.draft_id!=='string'||!/^[a-f0-9]{32}$/.test(origin.draft_id)))throw Error('Draft receipt must be null or 32 lowercase hex characters.');
 if(typeof origin.source_sha256!=='string'||!/^[a-f0-9]{64}$/.test(origin.source_sha256))throw Error('Origin source hash must be SHA-256.');
 if(origin.needs_review!==undefined&&origin.needs_review!==true)throw Error('Generated drafts require review.');
 if(origin.edited!==undefined&&typeof origin.edited!=='boolean')throw Error('Origin edited must be true or false.');
 if(origin.verification!==undefined)choice(origin.verification,['server_receipt','declared_import'],'Origin verification');
 return structuredClone({...origin,needs_review:true}) as unknown as DraftOrigin;
}
export function parseScienceBundle(source:string):{document:ScienceDocument;origin:DraftOrigin|null}{
 if(source.length>90000)throw Error('Storyboard file exceeds the 90 KB limit.');
 const value=JSON.parse(source);
 if(value&&typeof value==='object'&&Object.hasOwn(value,'document')){const envelope=record(value,['document','origin'],'Import envelope'),origin=parseScienceOrigin(envelope.origin);return {document:parseScienceDocument(envelope.document),origin:origin?{...origin,verification:'declared_import'}:null}}
 return {document:parseScienceDocument(value),origin:null};
}
export function scienceMotionAllowed(playing:boolean,reduced:boolean,visible:boolean,intersecting:boolean){return playing&&!reduced&&visible&&intersecting}
export function advanceSignal(progress:number,delta:number,speed:number,running:boolean){return running?(progress+Math.max(0,Math.min(delta,0.05))*speed*0.16)%1:progress}
