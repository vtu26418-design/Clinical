export const SCENES = ['neurons', 'molecule', 'dna', 'pipeline'] as const;
export type ScienceScene = typeof SCENES[number];
export type ScienceFocus = 'overview' | 'input' | 'transfer' | 'processing' | 'output';
export interface ScienceStep {id:string; title:string; caption:string; narration:string; focus:ScienceFocus; labels:string[]}
export interface ScienceSettings {
 accent:string; background:'midnight'|'light'; detail:'low'|'standard'; speed:0.5|1|1.5|2;
 show_labels:boolean; camera:'orbit'|'front'|'close'; voice_uri:string; voice_rate:number;
}
export interface ScienceDocument {version:1; title:string; source_notes:string; scene:ScienceScene; steps:ScienceStep[]; settings:ScienceSettings}
export interface StoryboardSummary {id:string; title:string; scene:ScienceScene; updated_at:string}
export interface StoryboardRecord extends StoryboardSummary {document:ScienceDocument;origin?:DraftOrigin|null}
export interface DraftOrigin {provider:string; model:string; generated:true;draft_id?:string|null;source_sha256:string;needs_review?:true;edited?:boolean;verification?:'server_receipt'|'declared_import'}
export interface ScienceStudioProps {scopeKey:string; canEdit:boolean; evidence?:{title:string; notes:string}}
