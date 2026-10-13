import {GuidedEvidence} from './EvidenceGuide';
import {journeyScene} from './guidedEvidence';
import type {Study} from '../../types';
import {PipelineDiagram} from './AnimatedPipeline';
import {ObservedDates,PhasePathway} from './TrialTimeline';
import {ExplanationChart} from './XAIAnimations';
import {durationEvidence,formatNumber} from './evidence';
import {AnimationPanel,Provenance,useMotion} from './shared';

export interface PredictionJourneyProps {study:Study;duration:any;phase?:any;provenance?:any;active?:boolean}
export function PredictionJourney({study,duration,phase,provenance,active=true}:PredictionJourneyProps) {
 const motion=useMotion(active),prediction=durationEvidence(duration),phaseAvailable=phase?.status==='available'&&phase?.is_demo!==true;
 const dates=['start_date','primary_completion_date','completion_date'].map(field=>{const value=typeof study[field]==='string'&&study[field].trim()?study[field]:null;return {field,label:field==='start_date'?'Study start':field==='primary_completion_date'?'Primary completion':'Study completion',value,precision:value?/^\d{4}-\d{2}-\d{2}$/.test(value)?'day':/^\d{4}-\d{2}$/.test(value)?'month':/^\d{4}$/.test(value)?'year':'unknown':null,date_type:study[`${field}_type`]||null}});
 return <AnimationPanel title="Prediction journey" description={`${study.nct_id} · saved-model evidence returned`} motion={motion} guided><GuidedEvidence {...journeyScene(study,duration,phase)} active={active} playing={motion.running} onPlayingChange={motion.setPlaying}/><PipelineDiagram hasStudy hasResult={prediction.available||phaseAvailable} modelName={duration?.model_name||phase?.model_name}/><div className="cti-prediction-journey-grid"><section className="cti-prediction-journey-card"><h3>Overall model result</h3><div className="cti-evidence-metrics"><div><span>Total duration</span><strong>{prediction.available?`${formatNumber(prediction.days)} days`:'Unavailable'}</strong></div><div><span>Predicted phase</span><strong>{phaseAvailable?phase.predicted_phase||'Unknown':'Unavailable'}</strong></div></div><p className="cti-animation-note">{prediction.available?duration.prediction_scope:prediction.reason}</p></section><section className="cti-prediction-journey-card"><PhasePathway reportedPhase={study.phase} predictedPhase={phaseAvailable?phase.predicted_phase:undefined}/></section><section className="cti-prediction-journey-card"><h3>Model explanation</h3><ExplanationChart explanation={duration?.duration_explanation||duration?.explanation}/></section><section className="cti-prediction-journey-card"><h3>Reported registry dates</h3><ObservedDates dates={dates}/><p className="cti-animation-note">Positions are illustrative. Stage-specific timings and treatment effects are not estimated.</p></section></div><Provenance data={provenance}/></AnimationPanel>;
}
