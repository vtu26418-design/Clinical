/** Tab-scoped navigation intent. Authorization always comes from bootstrap. */
export const workspaceSessionKey='cti.workspace-session.v5203';
export type WorkspaceIntent={userId:string;projectId:string;view:'workspace'|'projects'};
type SessionStorage=Pick<Storage,'getItem'|'setItem'|'removeItem'|'key'|'length'>;
export function readWorkspaceIntent(storage:SessionStorage):unknown{
  try{return JSON.parse(storage.getItem(workspaceSessionKey)||'null')}catch{return null}
}
export function resolveWorkspaceIntent(raw:unknown,userId:string|null,authorizedProjectIds:string[]):WorkspaceIntent{
  const safe:WorkspaceIntent={userId:userId||'',projectId:'',view:'projects'};
  if(!userId||!raw||typeof raw!=='object'||Array.isArray(raw))return safe;
  const value=raw as Partial<WorkspaceIntent>;
  if(value.userId!==userId||typeof value.projectId!=='string'||!authorizedProjectIds.includes(value.projectId)||!['workspace','projects'].includes(value.view||''))return safe;
  return {userId,projectId:value.projectId,view:value.view!};
}
export function writeWorkspaceIntent(storage:SessionStorage,intent:WorkspaceIntent){
  try{storage.setItem(workspaceSessionKey,JSON.stringify(intent));if(intent.projectId)storage.setItem('cti-project-id',intent.projectId);else storage.removeItem('cti-project-id')}catch{/* Private browsers can disable storage. */}
}
export function clearWorkspaceSession(storage:SessionStorage){
  try{const keys:string[]=[];for(let index=0;index<storage.length;index++){const key=storage.key(index);if(key&&(key===workspaceSessionKey||key==='cti-project-id'||key.startsWith('cti.workspace.')||key.startsWith('cti-dataset-')))keys.push(key)}keys.forEach(key=>storage.removeItem(key))}catch{/* No persisted selection is usable when storage is inaccessible. */}
}
