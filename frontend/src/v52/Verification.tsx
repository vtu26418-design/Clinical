import {useEffect,useState} from 'react';
import type {ReactNode} from 'react';
import {Mail,ShieldCheck} from 'lucide-react';
import {DEMO} from '../api';
import {v52Request} from './client';
import type {Verification} from './client';

export function VerificationPanel({blocking=false,onVerified}:{blocking?:boolean;onVerified?:()=>void}){
 const [status,setStatus]=useState<Verification|null>(null),[error,setError]=useState(''),[message,setMessage]=useState(''),[busy,setBusy]=useState(false);
 const load=()=>{if(DEMO)return;setBusy(true);setError('');v52Request<Verification>('/account/verification').then(s=>{setStatus(s);if(s.verified)onVerified?.()}).catch(e=>setError(e.message)).finally(()=>setBusy(false))};
 useEffect(load,[]);
 async function send(){setBusy(true);setError('');try{const r=await v52Request<{message:string}>('/account/verification/request',{method:'POST'});setMessage(r.message)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 return <section className={`v52-surface v52-verification ${blocking?'blocking':''}`}><ShieldCheck size={32}/><h2>{status?.verified?'Email verified':'Verify your email address'}</h2><p>{blocking?'Your operator requires a verified email before opening the workspace.':'Confirm your account email using a secure, expiring link.'}</p>{status?.email&&<strong>{status.email}</strong>}{error&&<p role="alert" className="v52-error">{error}</p>}{message&&<p role="status">{message}</p>}{DEMO?<p>Verification requires the authenticated server and a configured email delivery service.</p>:<><p>{status?.verified?'This account has confirmed its email address.':status?.reason||'Open the verification link sent to your inbox, then confirm it.'}</p><div><button className="btn primary" disabled={busy||!status?.available||status.verified} onClick={send}><Mail size={16}/>{busy?'Please wait…':'Send verification email'}</button><button className="btn secondary" disabled={busy} onClick={load}>Check status</button></div></>}</section>;
}

export function EmailVerificationLink({children}:{children:ReactNode}){
 const [token]=useState(()=>location.hash.startsWith('#verify-email?')?new URLSearchParams(location.hash.split('?')[1]).get('token')||'':'');
 const [confirmed,setConfirmed]=useState(false),[done,setDone]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 useEffect(()=>{if(token)history.replaceState(null,'',location.pathname+location.search)},[token]);
 async function confirm(){setBusy(true);setError('');try{await v52Request('/auth/verify-email',{method:'POST',body:JSON.stringify({token})});setConfirmed(true)}catch(e){setError((e as Error).message)}finally{setBusy(false)}}
 if(!token||done)return <>{children}</>;
 return <div className="v52-confirm"><section className="v52-surface"><ShieldCheck size={38}/><h1>{confirmed?'Email confirmed':'Confirm your email'}</h1><p>{confirmed?'Your email address is verified. Sign in to continue your research.':'Confirm that you requested this verification for your Clinical Trial Intelligence account.'}</p>{error&&<p role="alert" className="v52-error">{error}</p>}{confirmed?<button className="btn primary" onClick={()=>setDone(true)}>Continue to workbench</button>:<button className="btn primary" disabled={busy} onClick={confirm}>{busy?'Confirming…':'Confirm email address'}</button>}</section></div>;
}

export function VerificationGate({children}:{children:ReactNode}){
 const [status,setStatus]=useState<Verification|null>(null),[error,setError]=useState('');
 useEffect(()=>{if(DEMO)return;let alive=true;v52Request<Verification>('/account/verification').then(s=>{if(alive)setStatus(s)}).catch(e=>{if(alive)setError(e.message)});return()=>{alive=false}},[]);
 if(DEMO)return <>{children}</>;
 if(error)return <div className="v52-confirm"><section className="v52-surface"><h2>Account status unavailable</h2><p role="alert">{error}</p><button className="btn primary" onClick={()=>location.reload()}>Reconnect</button></section></div>;
 if(!status)return <div className="v5-loading" role="status">Checking account access…</div>;
 if(status.required&&!status.verified)return <div className="v52-confirm"><VerificationPanel blocking onVerified={()=>setStatus({...status,verified:true})}/></div>;
 return <>{children}</>;
}
