/** Educational summaries, verified against the linked primary sources on 2026-10-07. */
export type PhaseKey = '0' | '1' | '2' | '3' | '4';
export type PhaseLesson = {
  id: PhaseKey; roman: string; title: string; question: string; purpose: string;
  scale: string; scaleNote: string; focus: string; steps: readonly string[]; source: string;
};

export const PHASE_SOURCES = {
  fda: {label: 'FDA · Clinical research phases', url: 'https://www.fda.gov/patients/drug-development-process/step-3-clinical-research'},
  early: {label: 'NCI · Early-phase trials', url: 'https://dctd.cancer.gov/programs/dtc/about/about-dtc-clinical-trials'},
  design: {label: 'NCI · How clinical trials work', url: 'https://www.cancer.gov/research/participate/clinical-trials/how-trials-work'},
  combined: {label: 'NCI · Combined Phase I/II', url: 'https://www.cancer.gov/publications/dictionaries/cancer-terms/def/phase-1-phase-2-clinical-trial'},
  labels: {label: 'NIH NCATS · Phase terminology', url: 'https://toolkit.ncats.nih.gov/glossary/phases-of-clinical-trials/'},
};

export const PHASE_LESSONS: readonly PhaseLesson[] = [
  {id:'0', roman:'0', title:'Explore', question:'How does this drug behave in the body?',
    purpose:'An optional exploratory stage that examines drug behavior and biological response before broader testing.',
    scale:'A very small group', scaleNote:'Early exploratory research; protocols vary.', focus:'Drug behavior', source:'early',
    steps:['A small group enters an exploratory study.','The protocol defines exposure and sampling.','Researchers collect information about the drug in the body.','Observations inform further research; they do not establish benefit.']},
  {id:'1', roman:'I', title:'Find the dose', question:'What dose and safety profile warrant further study?',
    purpose:'Examine tolerability, dosing and side effects with close monitoring.',
    scale:'Often 20–100 people', scaleNote:'FDA drug-development example; cancer studies may be smaller.', focus:'Safety & dose', source:'fda',
    steps:['Participants enter protocol-defined groups.','Each illustrated group represents a dosing cohort.','Safety observations are collected and reviewed.','The design may adapt dosing; this diagram makes no dose recommendation.']},
  {id:'2', roman:'II', title:'Look for activity', question:'Is there evidence of activity, and what are the side effects?',
    purpose:'Study preliminary efficacy in people with the condition while gathering more safety information.',
    scale:'Up to several hundred', scaleNote:'Illustrative scale, not a phase definition.', focus:'Activity & safety', source:'fda',
    steps:['A group with the condition enters the study.','The illustrated design has one study arm; other designs exist.','Scheduled assessments record activity and safety.','Review the evidence and uncertainty, not a guaranteed benefit.']},
  {id:'3', roman:'III', title:'Compare', question:'How does the treatment compare in a larger study?',
    purpose:'Evaluate benefit and adverse reactions in a larger population.',
    scale:'Often 300–3,000 people', scaleNote:'FDA example; actual enrollment can differ substantially.', focus:'Comparative evidence', source:'fda',
    steps:['Eligible participants enter a comparative design.','In this example, chance assigns participants to two arms.','Both arms have scheduled assessments.','The study compares evidence across arms; no winning arm is shown.']},
  {id:'4', roman:'IV', title:'Keep learning', question:'What do we learn after approval?',
    purpose:'Continue investigating safety and effectiveness after approval.',
    scale:'Often thousands', scaleNote:'Post-approval studies vary in size and design.', focus:'Longer-term observation', source:'fda',
    steps:['The illustration begins after approval.','Participants are observed across several study sites.','Information is collected over further follow-up.','The research adds evidence about use after approval.']},
];

export const PHASE_QUIZ = [
  {question:'Which stage most directly focuses on dose and tolerability?', options:['Phase I','Phase III','Phase IV'], answer:0, explanation:'Phase I examines dosing and safety before broader testing.', phase:1},
  {question:'In the Phase III illustration, why are people assigned by chance?', options:['To guarantee identical results','To reduce allocation bias','To make every participant receive the new treatment'], answer:1, explanation:'Random assignment helps reduce bias when comparing groups. It does not guarantee a beneficial result.', phase:3},
  {question:'When does Phase IV research take place?', options:['Before human research','Only during dose finding','After approval'], answer:2, explanation:'Phase IV adds evidence after a treatment has been approved.', phase:4},
  {question:'What does a combined Phase I/II label tell you?', options:['The trial was automatically successful','One protocol addresses objectives from both phases','The phase is missing'], answer:1, explanation:'Combined studies can address safety and dose questions alongside preliminary activity questions.', phase:1},
  {question:'What does “Not applicable” mean in a registry phase field?', options:['The study necessarily failed','Every participant finished treatment','FDA-defined drug phases do not apply'], answer:2, explanation:'Some studies, including device or behavioral trials, do not use these phases. A missing value is a separate data-quality issue.', phase:null},
] as const;

/** Accept registry enum, AACT, numeric, and Roman labels without guessing from title. */
export function phaseKeys(value: unknown): PhaseKey[] {
  const raw = String(value ?? '').trim().toUpperCase();
  if (!raw || /^(NA|N\/A|NOT[ _-]?APPLICABLE|NONE|UNKNOWN|NOT REPORTED)$/.test(raw)) return [];
  if (/EARLY[ _-]?PHASE[ _-]?1|PHASE[ _-]?0/.test(raw) || raw === '0') return ['0'];
  const normalized = raw.replace(/PHASE/g, '').replace(/\bIV\b/g, '4').replace(/\bIII\b/g, '3').replace(/\bII\b/g, '2').replace(/\bI\b/g, '1');
  return [...new Set(normalized.split(/[^0-9]+/).filter((v): v is PhaseKey => /^[1-4]$/.test(v)))];
}
