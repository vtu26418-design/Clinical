import type {SceneKind} from './types';
export type ClinicZone='reception'|'screening'|'exam'|'sample'|'review'|'comparison'|'followup';
export type ClinicAction='welcome'|'screen'|'consult'|'sample'|'read'|'review'|'compare'|'followup';
export type ClinicPoint=[number,number,number];
export interface ClinicStage {zone:ClinicZone;action:ClinicAction}
const stage=(zone:ClinicZone,action:ClinicAction):ClinicStage=>({zone,action});
const workflows:Record<SceneKind,ClinicStage[]>={
 phase:[stage('reception','welcome')],
 recruitment:[stage('reception','welcome'),stage('screening','screen'),stage('screening','read'),stage('exam','consult'),stage('sample','sample'),stage('review','review'),stage('followup','followup')],
 pipeline:[stage('reception','read'),stage('review','read'),stage('sample','sample'),stage('comparison','compare'),stage('review','review'),stage('followup','consult')],
 xai:[stage('review','read'),stage('review','review'),stage('comparison','compare'),stage('followup','consult')],
 complexity:[stage('review','read'),stage('screening','screen'),stage('review','review'),stage('comparison','compare')],
 fusion:[stage('review','read'),stage('sample','sample'),stage('review','review'),stage('comparison','compare')],
 timeline:[stage('reception','welcome'),stage('screening','screen'),stage('exam','consult'),stage('followup','followup')],
 scenario:[stage('review','read'),stage('comparison','compare'),stage('comparison','review'),stage('followup','followup')],
 journey:[stage('reception','welcome'),stage('review','read'),stage('screening','screen'),stage('review','review'),stage('comparison','compare')],
 helix:[stage('sample','sample'),stage('sample','review'),stage('sample','read')],
};
const phases:ClinicStage[]=[stage('sample','sample'),stage('screening','screen'),stage('exam','consult'),stage('comparison','compare'),stage('followup','followup')];
/** Select a teaching activity, never infer study progression or measurements. */
export function resolveClinicStage(kind:SceneKind,step:number,phaseIndex?:number):ClinicStage{
 const index=Number.isFinite(step)?Math.max(0,Math.floor(step)):0;
 if(kind==='phase'&&phaseIndex!==undefined&&Number.isInteger(phaseIndex)&&phaseIndex>=0&&phaseIndex<phases.length){const context=phases[phaseIndex];return index===0?context:{zone:context.zone,action:index%2===1?'read':context.action}}
 const sequence=workflows[kind];return sequence[Math.min(index,sequence.length-1)];
}
/** Local animation time advances only while the shared viewport policy permits it. */
export function advanceClinicTime(time:number,delta:number,running:boolean,speed:number):number{return !running?time:time+(Number.isFinite(delta)?Math.max(0,Math.min(delta,0.05)):0)*(speed===0.5||speed===2?speed:1)}
/** Fixed illustrative travel, independent of dates, enrollment, outcomes and model values. */
export function clinicWalk(from:ClinicPoint,to:ClinicPoint,time:number){const progress=Math.max(0,Math.min(1,time/3)),smooth=progress*progress*(3-2*progress);return {position:from.map((value,index)=>value+(to[index]-value)*smooth) as ClinicPoint,walking:progress<1,heading:Math.atan2(to[0]-from[0],to[2]-from[2])}}
