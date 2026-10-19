import {platformRequest} from '../../v5/client';
import {parseScienceDocument,parseScienceOrigin} from './schema';
import type {DraftOrigin,ScienceDocument,ScienceScene,StoryboardRecord,StoryboardSummary} from './types';
const path='/science/storyboards';
async function checked(result:Promise<StoryboardRecord>){const record=await result;return {...record,document:parseScienceDocument(record.document),origin:parseScienceOrigin(record.origin)}}
export const scienceApi={
 list:()=>platformRequest<{items:StoryboardSummary[]}>(path),
 load:(id:string)=>checked(platformRequest<StoryboardRecord>(`${path}/${encodeURIComponent(id)}`)),
 save:(document:ScienceDocument,id?:string,updatedAt?:string,origin?:DraftOrigin|null)=>checked(platformRequest<StoryboardRecord>(id?`${path}/${encodeURIComponent(id)}`:path,{method:id?'PUT':'POST',body:JSON.stringify({document:parseScienceDocument(document),origin:parseScienceOrigin(origin),...(id&&updatedAt?{expected_updated_at:updatedAt}:{})})})),
 remove:(id:string)=>platformRequest(`${path}/${encodeURIComponent(id)}`,{method:'DELETE'}),
 draft:async(topic:string,source_notes:string,scene:ScienceScene,provider:string)=>{const result=await platformRequest<{document:ScienceDocument;origin:DraftOrigin}>('/science/draft',{method:'POST',body:JSON.stringify({topic,source_notes,scene,provider})},180000);return {...result,document:parseScienceDocument(result.document)}},
};
