import type {SceneValue} from './types';
export function normalizeValues(values:SceneValue[]=[]):SceneValue[]{return values.map(item=>({...item,value:typeof item.value==='number'&&Number.isFinite(item.value)?item.value:null}))}
export function formatSceneValue(item:SceneValue):string {return item.value===null||!Number.isFinite(item.value)?'Unknown':`${item.value.toLocaleString(undefined,{maximumFractionDigits:10})}${item.unit?` ${item.unit}`:''}`}
/** Scale only supplied evidence for presentation. Never infer missing measurements. */
export function signedBars(values:SceneValue[]=[]){const known=normalizeValues(values).filter((item):item is SceneValue&{value:number}=>item.value!==null);const largest=Math.max(0,...known.map(item=>Math.abs(item.value)));return known.map(item=>({...item,scaled:largest?item.value/largest:0}))}
export function canAnimate({playing,active,reduced,visible,intersecting}:{playing:boolean;active:boolean;reduced:boolean;visible:boolean;intersecting:boolean}){return playing&&active&&!reduced&&visible&&intersecting}
export function canNarrate({enabled,supported,active,visible,intersecting}:{enabled:boolean;supported:boolean;active:boolean;visible:boolean;intersecting:boolean}){return enabled&&supported&&active&&visible&&intersecting}
export function resolveSceneMode(preference:'auto'|'2d'|'3d',desktop:boolean,webgl:boolean):'2d'|'3d'{return webgl&&(preference==='3d'||preference==='auto'&&desktop)?'3d':'2d'}
export function clampStep(step:number,count:number){return count>0?Math.max(0,Math.min(count-1,Number.isFinite(step)?Math.floor(step):0)):0}
export function normalizeSpeed(speed:number){return speed===0.5||speed===2?speed:1}
/** Recruitment stages are independent reported participant counts. Sites and targets use HTML. */
export function recruitmentBars(values:SceneValue[]=[]){return signedBars(values.filter(item=>item.unit==='participants'&&item.status!=='planned target'&&item.value!==null&&item.value>=0))}
/** Presentation positions only; the provided PCI components and score are never recomputed. */
export function complexitySegments(values:SceneValue[]=[]){let bottom=0;return normalizeValues(values).filter((item):item is SceneValue&{value:number}=>item.value!==null&&item.value>=0).map(item=>{const height=item.value*0.025,segment={...item,bottom,height};bottom+=height;return segment})}
