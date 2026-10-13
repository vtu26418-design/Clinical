import type {ReactNode} from 'react';
export type SceneKind = 'phase'|'pipeline'|'xai'|'recruitment'|'complexity'|'fusion'|'timeline'|'scenario'|'journey'|'helix';
export interface SceneValue {label:string; value:number|null; unit?:string; status?:string}
export interface SceneStep {title:string; detail:string}
export interface ScenePanelProps {
 kind:SceneKind; title:string; subtitle?:string; steps:SceneStep[]; values?:SceneValue[]; labels?:string[];
 mode:'conceptual'|'evidence'|'planning'; step?:number; onStepChange?:(step:number)=>void;
 playing?:boolean; onPlayingChange?:(playing:boolean)=>void; speed?:number; onSpeedChange?:(speed:number)=>void;
 fallback?:ReactNode; active?:boolean; modelLabel?:string; phaseIndex?:number;
}
