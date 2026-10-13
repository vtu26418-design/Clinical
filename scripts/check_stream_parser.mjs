/** Exercise the real browser SSE parser with byte-boundary and failure cases. */
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const require=createRequire(new URL('../frontend/package.json',import.meta.url));
const {build}=require('esbuild');
const bundle=await build({entryPoints:[fileURLToPath(new URL('../frontend/src/v52/streamChat.ts',import.meta.url))],bundle:true,write:false,format:'esm',define:{'import.meta.env.VITE_API_BASE_URL':'"/api/v1"'}});
const {streamChat}=await import('data:text/javascript;base64,'+Buffer.from(bundle.outputFiles[0].text).toString('base64'));
globalThis.sessionStorage={getItem:()=> 'test-project'};
const data={message:'Test',dataset_id:'test-data',provider:'anthropic',profile:'balanced'};
function streamResponse(content,size=7){const bytes=new TextEncoder().encode(content);let position=0;return new Response(new ReadableStream({pull(controller){if(position>=bytes.length){controller.close();return}controller.enqueue(bytes.slice(position,position+size));position+=size}}),{headers:{'content-type':'text/event-stream'}})}
const sse='event: meta\r\ndata: {"provider":"Claude","model":"test"}\r\n\r\nevent: delta\r\ndata: {"text":"Evidence α"}\r\n\r\nevent: done\r\ndata: {"messages":[{"role":"assistant","content":"Evidence α"}]}\r\n\r\n';
for(const size of [1,2,7,10000]){globalThis.fetch=async()=>streamResponse(sse,size);let text='',meta;const result=await streamChat('id',data,t=>text+=t,m=>meta=m,new AbortController().signal);assert.equal(text,'Evidence α');assert.equal(meta.provider,'Claude');assert.equal(result.messages[0].content,text)}
globalThis.fetch=async()=>streamResponse('event: delta\ndata: {"text":"Partial"}\n\n');await assert.rejects(streamChat('id',data,()=>{},()=>{},new AbortController().signal),/closed before/);
globalThis.fetch=async()=>streamResponse('event: error\ndata: {"message":"Provider unavailable"}\n\n');await assert.rejects(streamChat('id',data,()=>{},()=>{},new AbortController().signal),/Provider unavailable/);
globalThis.fetch=async()=>new Response(JSON.stringify({detail:'Provider is not configured'}),{status:503});await assert.rejects(streamChat('id',data,()=>{},()=>{},new AbortController().signal),/not configured/);
globalThis.fetch=async()=>streamResponse('event: delta\ndata: '+JSON.stringify({text:'x'.repeat(20001)})+'\n\n',30000);await assert.rejects(streamChat('id',data,()=>{},()=>{},new AbortController().signal),/display limit/);
globalThis.fetch=async()=>streamResponse('event: meta\ndata: {"output_char_limit":96000}\n\nevent: delta\ndata: '+JSON.stringify({text:'x'.repeat(30000)})+'\n\nevent: done\ndata: {"messages":[]}\n\n',50000);let extended='';await streamChat('id',data,t=>extended+=t,()=>{},new AbortController().signal);assert.equal(extended.length,30000);
console.log('SSE parser: 9 checks passed (byte boundaries, UTF-8, CRLF, truncation, error, HTTP failure, output limit).');
