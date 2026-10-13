export type Evidence={source:'clinicaltrials'|'pubmed'|'openfda';id:string;title:string;summary:string;url:string;citation:string;published_at:string|null;retrieved_at:string};
export type Bookmark={id:string;project_id:string;created_by:string;created_at:string;evidence:Evidence};
export type Verification={required:boolean;verified:boolean;verified_at:string|null;delivery_configured:boolean;available:boolean;reason:string|null;email:string|null};
const base=(import.meta.env.VITE_API_BASE_URL||'/api/v1').replace(/\/v1\/?$/,'/v5.2');
export async function v52Request<T>(path:string,options:RequestInit={}):Promise<T>{
 const headers=new Headers(options.headers),project=sessionStorage.getItem('cti-project-id');
 if(project)headers.set('X-Project-ID',project);
 if(options.body)headers.set('Content-Type','application/json');
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),45000);
 try{const response=await fetch(base+path,{...options,headers,credentials:'include',signal:controller.signal});const body=await response.json().catch(()=>({detail:`Request failed (${response.status}).`}));if(!response.ok)throw new Error(typeof body.detail==='string'?body.detail:'The request could not be completed.');return body as T;}catch(e){if(e instanceof DOMException&&e.name==='AbortError')throw new Error('The source did not respond in time. Please retry.');throw e}finally{clearTimeout(timer)}
}
