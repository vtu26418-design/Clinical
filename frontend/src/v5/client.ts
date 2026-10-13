import {DEMO} from '../api';
import type {Dataset} from '../types';
import type {AssistantFeedback,AuditEvent,Bootstrap,ChatMessage,Conversation,InvitationResult,Member,Profile,Project,ProjectSettings} from './types';

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api/v1').replace(/\/v1\/?$/, '/v5');
const PREVIEW_KEY = 'cti-v5-preview-v1';
type Preview = {projects:Project[];conversations:Record<string,Conversation[]>};
const previewProject:Project = {id:'preview-project',name:'Clinical research',description:'Local software-test workspace. No remote database or AI provider is connected.',role:'owner',settings:{chat_daily_limit:50,chat_retention_days:90,default_provider:'auto',default_profile:'balanced',allow_ai:true,chat_max_output_tokens:16000,chat_context_chars:120000}};
let preview:Preview;
function fixture():Preview {
  if(preview)return preview;
  try {const stored=JSON.parse(localStorage.getItem(PREVIEW_KEY)||'null');if(Array.isArray(stored?.projects)&&stored.projects.length&&stored.conversations){preview=stored;return preview}}catch {/* An unavailable storage area keeps fixtures in memory. */}
  preview={projects:[structuredClone(previewProject)],conversations:{}};return preview;
}
function persist(){try{localStorage.setItem(PREVIEW_KEY,JSON.stringify(fixture()))}catch {/* Preview remains usable in memory. */}}
function projectId(){return sessionStorage.getItem('cti-project-id')||'preview-project'}
function conversationList(){const state=fixture(),id=projectId();return state.conversations[id]||(state.conversations[id]=[])}
function clone<T>(value:T):T{return structuredClone(value)}
export function errorText(error:unknown){return error instanceof Error?error.message:'Something went wrong. Please retry.'}
export async function platformRequest<T>(path:string,options:RequestInit={},timeoutMs=90000):Promise<T>{
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeoutMs);
  const headers=new Headers(options.headers);
  if(options.body&&!(options.body instanceof FormData))headers.set('Content-Type','application/json');
  const id=sessionStorage.getItem('cti-project-id');if(id)headers.set('X-Project-ID',id);
  try{
    const response=await fetch(`${BASE}${path}`,{...options,headers,credentials:'include',signal:controller.signal});
    const body=response.status===204?{}:await response.json().catch(()=>({detail:`Request failed (${response.status}).`}));
    if(!response.ok){if(response.status===401&&!path.startsWith('/auth/'))window.dispatchEvent(new Event('cti-session-expired'));throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail||body))}
    return body as T;
  }catch(error){if(error instanceof DOMException&&error.name==='AbortError')throw new Error('This request timed out. Check the service and retry.');if(error instanceof TypeError)throw new Error('Cannot reach the project service. Check that the backend is running and retry.');throw error}
  finally{clearTimeout(timer)}
}
const body=(value:unknown)=>JSON.stringify(value);
export const platformApi={
  bootstrap:async():Promise<Bootstrap>=>DEMO?{auth_required:false,setup_required:false,user:{id:'preview-user',email:'preview@local.invalid',name:'Preview researcher'},projects:clone(fixture().projects),database:{backend:'browser',label:'Local preview fixtures'},capabilities:{preview:true}}:platformRequest('/bootstrap'),
  login:(data:{email:string;password:string})=>platformRequest('/auth/login',{method:'POST',body:body(data)}),
  setup:(data:{email:string;password:string;name:string;setup_token:string})=>platformRequest('/auth/setup',{method:'POST',body:body(data)}),
  acceptInvite:(data:{token:string;password:string;name:string})=>platformRequest('/auth/accept-invite',{method:'POST',body:body(data)}),
  logout:()=>DEMO?Promise.resolve({}):platformRequest('/auth/logout',{method:'POST'}),
  logoutAll:()=>platformRequest('/auth/logout-all',{method:'POST'}),
  changePassword:(data:{current_password:string;new_password:string})=>platformRequest('/auth/password',{method:'POST',body:body(data)}),
  createProject:async(data:{name:string;description:string}):Promise<Project>=>{if(!DEMO)return platformRequest('/projects',{method:'POST',body:body(data)});const p:Project={...data,id:crypto.randomUUID(),role:'owner',settings:clone(previewProject.settings),created_at:new Date().toISOString()};fixture().projects.push(p);persist();return clone(p)},
  settings:async(id:string):Promise<ProjectSettings>=>DEMO?clone(fixture().projects.find(p=>p.id===id)!.settings):platformRequest(`/projects/${encodeURIComponent(id)}/settings`),
  updateSettings:async(id:string,settings:ProjectSettings):Promise<ProjectSettings>=>{if(!DEMO)return platformRequest(`/projects/${encodeURIComponent(id)}/settings`,{method:'PUT',body:body(settings)});const project=fixture().projects.find(p=>p.id===id)!;project.settings={...project.settings,...settings};persist();return clone(project.settings)},
  members:async(id:string):Promise<{items:Member[]}>=>DEMO?{items:[{user_id:'preview-user',email:'preview@local.invalid',name:'Preview researcher',role:'owner'}]}:platformRequest(`/projects/${encodeURIComponent(id)}/members`),
  addMember:(id:string,data:Record<string,string>)=>platformRequest<InvitationResult>(`/projects/${encodeURIComponent(id)}/members`,{method:'POST',body:body(data)}),
  removeMember:(projectId:string,userId:string)=>platformRequest(`/projects/${encodeURIComponent(projectId)}/members/${encodeURIComponent(userId)}`,{method:'DELETE'}),
  usage:async(id:string):Promise<Record<string,unknown>>=>DEMO?{conversations:conversationList().length,datasets:1,source:'Local preview fixtures'}:platformRequest(`/projects/${encodeURIComponent(id)}/usage`),
  audit:async(id:string):Promise<{items:AuditEvent[]}>=>DEMO?{items:[]}:platformRequest(`/projects/${encodeURIComponent(id)}/audit`),
  feedback:(messageId:string,data:{rating:number;comment:string;dataset_id?:string})=>platformRequest<{status:string;feedback:AssistantFeedback}>(`/messages/${encodeURIComponent(messageId)}/feedback`,{method:'POST',body:body(data)}),
  assistantFeedback:(projectId:string,status?:AssistantFeedback['review_status'])=>DEMO?Promise.resolve({items:[] as AssistantFeedback[],limit:200}):platformRequest<{items:AssistantFeedback[];limit:number}>(`/projects/${encodeURIComponent(projectId)}/assistant-feedback${status?`?status=${encodeURIComponent(status)}`:''}`),
  reviewFeedback:(projectId:string,feedbackId:string,data:{status:AssistantFeedback['review_status'];correction:string})=>platformRequest<{feedback:AssistantFeedback}>(`/projects/${encodeURIComponent(projectId)}/assistant-feedback/${encodeURIComponent(feedbackId)}`,{method:'PUT',body:body(data)}),
  conversations:async():Promise<{items:Conversation[]}>=>DEMO?{items:clone(conversationList())}:platformRequest('/conversations'),
  createConversation:async(title:string,dataset_id?:string):Promise<Conversation>=>{if(!DEMO)return platformRequest('/conversations',{method:'POST',body:body({title})});const conversation:Conversation={id:crypto.randomUUID(),title,dataset_id,created_at:new Date().toISOString(),updated_at:new Date().toISOString(),messages:[]};conversationList().unshift(conversation);persist();return clone(conversation)},
  conversation:async(id:string):Promise<Conversation>=>{if(!DEMO)return platformRequest(`/conversations/${encodeURIComponent(id)}`);const item=conversationList().find(c=>c.id===id);if(!item)throw new Error('Conversation not found in this preview workspace.');return clone(item)},
  renameConversation:async(id:string,title:string):Promise<Conversation>=>{if(!DEMO)return platformRequest(`/conversations/${encodeURIComponent(id)}`,{method:'PATCH',body:body({title})});const item=conversationList().find(c=>c.id===id)!;item.title=title;persist();return clone(item)},
  deleteConversation:async(id:string)=>{if(!DEMO)return platformRequest(`/conversations/${encodeURIComponent(id)}`,{method:'DELETE'});fixture().conversations[projectId()]=conversationList().filter(c=>c.id!==id);persist();return {}},
  message:(id:string,data:{message:string;dataset_id:string;nct_id?:string;provider:string;profile:Profile})=>platformRequest<Conversation&{reply?:string;messages:ChatMessage[]}>(`/conversations/${encodeURIComponent(id)}/messages`,{method:'POST',body:body(data)},180000),
  importUrl:(url:string,name:string)=>platformRequest<Dataset>('/import/url',{method:'POST',body:body({url,name})},180000),
  importPaste:(content:string,format:string,name:string)=>platformRequest<Dataset>('/import/paste',{method:'POST',body:body({content,format,name})},180000),
};
