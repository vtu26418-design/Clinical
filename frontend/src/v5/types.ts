export type Role = 'owner' | 'researcher' | 'reviewer' | 'viewer';
export const roleLabels:Record<Role,string>={owner:'Owner',researcher:'Trial researcher',reviewer:'Clinical reviewer',viewer:'Viewer'};
export type Capability='read_research'|'predict'|'explain'|'charts'|'export'|'write_research'|'run_scenarios'|'train_models'|'approve_models'|'activate_models'|'manage_members'|'manage_settings'|'chat'|'review_protocol'|'view_audit';
export type Capabilities=Record<Capability,boolean>;
export function projectCapabilities(project:{role:Role;capabilities?:Partial<Capabilities>}):Capabilities{
  const owner=project.role==='owner',writer=owner||project.role==='researcher',reviewer=owner||project.role==='reviewer';
  return {read_research:true,predict:true,explain:true,charts:true,export:true,write_research:writer,run_scenarios:writer,train_models:owner,approve_models:owner,activate_models:owner,manage_members:owner,manage_settings:owner,chat:project.role!=='viewer',review_protocol:reviewer,view_audit:reviewer,...project.capabilities};
}
export type User = {id:string;email:string;name:string};
export type ProjectSettings = {
  chat_daily_limit?:number; chat_retention_days?:number; default_provider?:string;
  default_profile?:'fast'|'balanced'|'deep'; allow_ai?:boolean;
  chat_max_output_tokens?:number;chat_context_chars?:number;
  [key:string]:unknown;
};
export type Project = {id:string;name:string;description?:string;role:Role;settings:ProjectSettings;created_at?:string;capabilities?:Partial<Capabilities>;study_count?:number};
export type Bootstrap = {
  auth_required:boolean; setup_required:boolean; user:User|null; projects:Project[];
  database:string|{backend?:string;engine?:string;mode?:string;label?:string;[key:string]:unknown};
  capabilities?:Record<string,unknown>; mode?:string;
};
export type Member = {id?:string;user_id?:string;email:string;name:string;role:Role;created_at?:string};
export type InvitationResult=Member&{invitation_token?:string;expires_in_seconds?:number;acceptance_url?:string};
export type AuditEvent={id?:string;action?:string;user_id?:string;created_at?:string;details?:unknown;[key:string]:unknown};
export type AssistantFeedback={id:string;project_id:string;user_id:string;conversation_id:string;message_id:string;dataset_id?:string;rating:number;comment:string;created_at:string;updated_at?:string;review_status:'pending'|'approved'|'rejected';correction?:string;reviewed_by?:string;reviewed_at?:string;assistant_reply?:string;question?:string;source_references?:Reference[]};
export type Reference = {id?:string;label?:string;title?:string;type?:string;nct_id?:string;dataset_id?:string;url?:string;snippet?:string;[key:string]:unknown};
export type ChatMessage = {id:string;role:'user'|'assistant'|'system';content:string;status?:string;error?:string;created_at?:string;provider?:string;model?:string;profile?:string;references?:Reference[];context_references?:Reference[];citations?:Reference[];metadata?:Record<string,unknown>};
export type Conversation = {id:string;title:string;created_at?:string;updated_at?:string;dataset_id?:string;messages?:ChatMessage[];message_count?:number};
export type Provider = {id:string;label:string;configured:boolean;model:string};
export type Routing = {enabled:boolean;mode:string;selected_provider:string|null;selected_label:string;model:string|null;priority:string[];auto_fallback:boolean;providers:Provider[];selection_note:string};
export type Profile = 'fast' | 'balanced' | 'deep';
