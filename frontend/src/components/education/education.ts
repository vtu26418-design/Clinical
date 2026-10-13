import {PHASE_LESSONS} from '../../phaseContent';
import type {ScenePanelProps} from '../three/types';

export const lessons = PHASE_LESSONS;
export const PHASE_STEP_NAMES = ['Participants', 'Study design', 'Observations', 'Review'] as const;

/** Only original source-backed teaching text enters the conceptual scene. Symbols never encode counts. */
export function phaseScene(index: number | null | undefined): Pick<ScenePanelProps,'kind'|'title'|'subtitle'|'steps'|'values'|'labels'|'mode'|'phaseIndex'> | null {
  if (typeof index !== 'number' || !Number.isInteger(index) || index < 0 || index >= PHASE_LESSONS.length) return null;
  const phase = PHASE_LESSONS[index];
  return {
    kind: 'phase', title: `Phase ${phase.roman}: ${phase.title}`,
    subtitle: 'Participant and site symbols are illustrative; they do not encode actual enrollment, outcomes, benefit or dose recommendations.',
    steps: phase.steps.map((detail, step) => ({title: PHASE_STEP_NAMES[step], detail})),
    values: [], labels: [...PHASE_STEP_NAMES], mode: 'conceptual', phaseIndex: index,
  };
}

/** Shared useMotion has already combined app and operating-system preferences. */
export function educationPlayback(requested: boolean, motion: {running:boolean;reduced:boolean}): boolean {
  return requested && motion.running && !motion.reduced;
}

export const RESEARCH_JOURNEY = [
  {title: 'Import', detail: 'Import trial records and check field coverage, missing values and data provenance before analysis.', action: 'Import and validate records', route: 'data'},
  {title: 'Review', detail: 'Open the selected study. Check its recorded phase, dates, enrollment and linked source evidence.', action: 'Review study records', route: 'explorer'},
  {title: 'Predict', detail: 'Choose a saved model appropriate to the research question. Inspect the artifact and supported input modalities before applying it.', action: 'Open Prediction Studio', route: 'predict'},
  {title: 'Interpret', detail: 'Review the model output, uncertainty and available feature attributions alongside provenance. Attributions describe the model, not causal effects.', action: 'Inspect explainability', route: 'xai'},
  {title: 'Compare', detail: 'Compare explicit scenario assumptions with the source record and selected-model output. A hypothetical change is research planning, not a treatment recommendation.', action: 'Compare a scenario', route: 'digital-twin'},
] as const;
