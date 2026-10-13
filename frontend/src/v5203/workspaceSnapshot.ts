export interface WorkspaceSnapshot {route:string;datasetId:string;selectedStudy:string;query:string;phase:string;status:string;sort:string;offset:number;moreOpen:boolean}
const defaults:WorkspaceSnapshot={route:'overview',datasetId:'sample-fixture',selectedStudy:'',query:'',phase:'',status:'',sort:'nct_id',offset:0,moreOpen:false};
function text(value:unknown,max:number,fallback=''){return typeof value==='string'&&value.length<=max?value:fallback}
function validate(raw:unknown,routes:readonly string[]):WorkspaceSnapshot {
 const value=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw as Record<string,unknown>:{};
 return {route:typeof value.route==='string'&&routes.includes(value.route)?value.route:'overview',datasetId:text(value.datasetId,200,'sample-fixture')||'sample-fixture',selectedStudy:text(value.selectedStudy,100),query:text(value.query,500),phase:text(value.phase,100),status:text(value.status,100),sort:['nct_id','title','enrollment'].includes(String(value.sort))?String(value.sort):'nct_id',offset:typeof value.offset==='number'&&Number.isInteger(value.offset)&&value.offset>=0&&value.offset<=100000?value.offset:0,moreOpen:value.moreOpen===true};
}
export function loadWorkspaceSnapshot(storage:Pick<Storage,'getItem'>,key:string,routes:readonly string[]):WorkspaceSnapshot {try{return validate(JSON.parse(storage.getItem(key)||'null'),routes)}catch{return {...defaults}}}
export function saveWorkspaceSnapshot(storage:Pick<Storage,'setItem'>,key:string,value:unknown,routes:readonly string[]):boolean {try{storage.setItem(key,JSON.stringify(validate(value,routes)));return true}catch{return false}}
export function workspaceRoute(hash:string,routes:readonly string[],savedRoute:string):string {const route=hash.replace(/^#/,'');if(!route)return routes.includes(savedRoute)?savedRoute:'overview';return routes.includes(route)?route:'overview'}
