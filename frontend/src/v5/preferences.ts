/** Only appearance is portable; project state and credentials never belong here. */
export const preferenceKey='cti.preferences.v5203';
export type Preferences={theme:'system'|'light'|'dark';motion:'system'|'reduced';chartLabels:'comfortable'|'compact';chartGrid:'show'|'hide';sceneMode:'auto'|'2d'|'3d';sceneQuality:'low'|'standard';narration:'off'|'on';density:'comfortable'|'compact'};
export const defaultPreferences:Preferences={theme:'system',motion:'system',chartLabels:'comfortable',chartGrid:'show',sceneMode:'auto',sceneQuality:'standard',narration:'off',density:'comfortable'};
const options:Record<keyof Preferences,readonly string[]>={theme:['system','light','dark'],motion:['system','reduced'],chartLabels:['comfortable','compact'],chartGrid:['show','hide'],sceneMode:['auto','2d','3d'],sceneQuality:['low','standard'],narration:['off','on'],density:['comfortable','compact']};
type DeviceStorage=Pick<Storage,'getItem'|'setItem'>;
function deviceStorage():DeviceStorage|null{try{return localStorage}catch{return null}}
function object(value:unknown):value is Record<string,unknown>{return !!value&&typeof value==='object'&&!Array.isArray(value)}
function validatePreferences(value:unknown):Preferences{
  if(!object(value)||Object.keys(value).length!==Object.keys(options).length)throw Error('Appearance file must contain exactly the supported preferences.');
  const result={...defaultPreferences};
  for(const key of Object.keys(value)){if(!Object.hasOwn(options,key)||typeof value[key]!=='string'||!options[key as keyof Preferences].includes(value[key] as string))throw Error(`Invalid appearance preference: ${key}.`);Object.assign(result,{[key]:value[key]})}
  return result;
}
export function readPreferences(storage:DeviceStorage|null=deviceStorage()):Preferences{
  try{
    const current=storage?.getItem(preferenceKey);if(current)return validatePreferences(JSON.parse(current));
    const legacy:unknown=JSON.parse(storage?.getItem('cti.preferences.v5202')||'{}'),result={...defaultPreferences};
    if(object(legacy))for(const key of ['theme','motion','chartLabels','chartGrid'] as const){if(typeof legacy[key]==='string'&&options[key].includes(legacy[key] as string))Object.assign(result,{[key]:legacy[key]})}
    storage?.setItem(preferenceKey,JSON.stringify(result));return result;
  }catch{return {...defaultPreferences}}
}
export function exportPreferences(value:Preferences){return JSON.stringify({schema:'cti.appearance',version:1,preferences:validatePreferences(value)},null,2)}
export function importPreferences(contents:string):Preferences{
  if(contents.length>16384)throw Error('Appearance file is too large.');
  const value:unknown=JSON.parse(contents);
  if(!object(value)||Object.keys(value).sort().join(',')!=='preferences,schema,version'||value.schema!=='cti.appearance'||value.version!==1)throw Error('Choose a CTI appearance export (version 1).');
  return validatePreferences(value.preferences);
}
export function applyPreferences(value:Preferences,root:Pick<HTMLElement,'dataset'>=document.documentElement,systemDark=window.matchMedia('(prefers-color-scheme: dark)').matches,dispatch:(event:Event)=>unknown=event=>window.dispatchEvent(event)){
  root.dataset.ctiTheme=value.theme==='system'?(systemDark?'dark':'light'):value.theme;
  root.dataset.ctiMotion=value.motion;root.dataset.ctiChartLabels=value.chartLabels;root.dataset.ctiChartGrid=value.chartGrid;
  root.dataset.ctiSceneMode=value.sceneMode;root.dataset.ctiSceneQuality=value.sceneQuality;root.dataset.ctiNarration=value.narration;root.dataset.ctiDensity=value.density;
  dispatch(new CustomEvent('cti-preferences-changed',{detail:{...value}}));
}
export function savePreferences(value:Preferences,storage:DeviceStorage|null=deviceStorage()):boolean{try{if(!storage)return false;storage.setItem(preferenceKey,JSON.stringify(validatePreferences(value)));return true}catch{return false}}
