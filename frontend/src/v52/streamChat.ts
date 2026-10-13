import type {ChatMessage,Conversation,Profile,Reference} from '../v5/types';

export type StreamMeta={provider?:string;model?:string;references?:Reference[];output_char_limit?:number};
export type StreamReply=Conversation&{reply?:string;messages:ChatMessage[]};
export async function streamChat(id:string,data:{message:string;dataset_id:string;nct_id?:string;provider:string;profile:Profile},onDelta:(text:string)=>void,onMeta:(meta:StreamMeta)=>void,signal:AbortSignal):Promise<StreamReply>{
 const base=(import.meta.env.VITE_API_BASE_URL||'/api/v1').replace(/\/v1\/?$/,'/v5');
 const headers=new Headers({'Content-Type':'application/json','Accept':'text/event-stream'});
 const project=sessionStorage.getItem('cti-project-id');if(project)headers.set('X-Project-ID',project);
 const response=await fetch(`${base}/conversations/${encodeURIComponent(id)}/messages/stream`,{method:'POST',headers,credentials:'include',body:JSON.stringify(data),signal});
 if(!response.ok){const body=await response.json().catch(()=>({detail:'The assistant request failed.'}));throw new Error(typeof body.detail==='string'?body.detail:`Assistant request failed (${response.status}).`)}
 if(!response.body||!response.headers.get('content-type')?.includes('text/event-stream'))throw new Error('The server did not return an assistant stream.');
 const reader=response.body.getReader(),decoder=new TextDecoder();let pending='',done:StreamReply|undefined,output=0,outputLimit=20000;
 function event(block:string){let kind='message';const data:string[]=[];for(const line of block.split('\n')){if(line.startsWith('event:'))kind=line.slice(6).trim();if(line.startsWith('data:'))data.push(line.slice(5).trimStart())}if(!data.length)return;
  const value=JSON.parse(data.join('\n'));
  if(kind==='meta'){if(Number.isInteger(value.output_char_limit)&&value.output_char_limit>=20000&&value.output_char_limit<=786432)outputLimit=value.output_char_limit;onMeta(value)}
  if(kind==='delta'&&typeof value.text==='string'){output+=value.text.length;if(output>outputLimit)throw new Error('Assistant response exceeded the display limit.');onDelta(value.text)}
  if(kind==='error')throw new Error(typeof value.message==='string'?value.message:'The assistant stream failed.');
  if(kind==='done'){if(!Array.isArray(value.messages))throw new Error('The assistant completion was incomplete.');done=value}
 }
 try{while(true){const chunk=await reader.read();pending=(pending+(chunk.done?decoder.decode():decoder.decode(chunk.value,{stream:true}))).replace(/\r\n/g,'\n');if(pending.length>8_000_000)throw new Error('Assistant event exceeded the size limit.');let boundary;while((boundary=pending.indexOf('\n\n'))>=0){event(pending.slice(0,boundary));pending=pending.slice(boundary+2)}if(done){await reader.cancel();return done}if(chunk.done)break}if(pending.trim())event(pending);if(done)return done;throw new Error('The connection closed before the assistant completed. Partial text was not confirmed as a saved answer.')}finally{try{await reader.cancel()}finally{reader.releaseLock()}}
}
