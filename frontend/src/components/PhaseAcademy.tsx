import {useEffect, useId, useMemo, useRef, useState} from 'react';
import type {KeyboardEvent} from 'react';
import {ArrowRight, ArrowUpRight, BookOpen, Check, ChevronRight, CircleHelp, FlaskConical, Pause, Play, RotateCcw, ShieldCheck, SkipForward, Sparkles, Users} from 'lucide-react';
import type {Study} from '../types';
import {Notice, nice, number} from './Shared';
import {PHASE_LESSONS, PHASE_QUIZ, PHASE_SOURCES, phaseKeys} from '../phaseContent';
import type {PhaseLesson} from '../phaseContent';
import './phaseAcademy.css';

const STEP_NAMES = ['Participants', 'Study design', 'Observations', 'Review'];
const stageIcons = [Sparkles, FlaskConical, Users, ShieldCheck, BookOpen];

function useReducedMotion() {
  const [reduced, setReduced] = useState(() => typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReduced(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  return reduced;
}

function People({x,y,count,columns=4,color='#088b83'}:{x:number;y:number;count:number;columns?:number;color?:string}) {
  return <g aria-hidden="true">{Array.from({length:count},(_,i)=><g key={i} transform={`translate(${x+(i%columns)*25} ${y+Math.floor(i/columns)*36})`} fill={color}><circle cy="-5" r="4.5"/><path d="M-7 13v-7a7 7 0 0 1 14 0v7z" opacity=".82"/></g>)}</g>;
}

function Diagram({phase,step,prefix}:{phase:PhaseLesson;step:number;prefix:string}) {
  const stage = Number(phase.id);
  const muted = '#8ca1ac';
  const active = '#088b83';
  const highlight = (n:number) => step === n || (step === 3 && n === 2);
  return <svg className="pa-diagram" viewBox="0 0 720 286" role="img" aria-labelledby={`${prefix}-diagram-title ${prefix}-diagram-desc`}>
    <title id={`${prefix}-diagram-title`}>Phase {phase.roman}: conceptual study structure</title>
    <desc id={`${prefix}-diagram-desc`}>{phase.steps[step]} Participant symbols are illustrative and do not encode enrollment, outcomes, or success rates.</desc>
    <defs><marker id={`${prefix}-arrow`} markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0 0L6 3L0 6" fill="#a8bbc3"/></marker></defs>
    {[{x:15,w:174,label:stage===4?'STUDY SITES':'PARTICIPANTS'},{x:218,w:263,label:stage===3?'COMPARISON ARMS':stage===1?'DOSING COHORTS':'STUDY DESIGN'},{x:510,w:195,label:'OBSERVATIONS'}].map((box,i)=><g key={box.label}>
      <rect className="pa-diagram-box" x={box.x} y="37" width={box.w} height="218" rx="13" fill={highlight(i)?'#eef9f7':'#f7f9fb'} stroke={highlight(i)?'#69bfb7':'#e2e9ed'} strokeWidth={highlight(i)?1.5:1}/>
      <text x={box.x+16} y="24" fill={highlight(i)?active:muted} fontSize="10" fontWeight="700" letterSpacing="1">{box.label}</text>
    </g>)}
    <path d="M190 146H211M482 146H503" stroke="#a8bbc3" strokeWidth="1.8" markerEnd={`url(#${prefix}-arrow)`}/>
    {stage===4?<g>{[0,1,2].map((_,i)=><g key={i} transform={`translate(${49+i%2*70} ${82+Math.floor(i/2)*89})`}><path d="M-17 13V-13H17V13M-7 13V-2H7V13" stroke={active} strokeWidth="2" fill="none"/><path d="M-5-8H5M0-13V-3" stroke={active} strokeWidth="2"/><text y="32" textAnchor="middle" fill="#526b78" fontSize="10">Site {i+1}</text></g>)}</g>:<>
      <People x={stage===0?77:63} y={stage===0?105:84} count={stage===0?4:stage===1?6:12} columns={stage===0?2:3}/>
      <text x="102" y="224" textAnchor="middle" fill="#526b78" fontSize="11">{stage===0?'Exploratory group':stage===1?'Small study groups':'People with the condition'}</text>
    </>}
    {stage===0?<g><rect x="253" y="75" width="194" height="62" rx="10" fill="#fff" stroke="#dce7ea"/><path d="M278 93v20a9 9 0 0 0 18 0V93M275 92h24M279 107h15" stroke={active} strokeWidth="2" fill="none"/><text x="310" y="102" fill="#193947" fontSize="12" fontWeight="600">Exploratory exposure</text><text x="310" y="119" fill="#526b78" fontSize="10">Protocol-defined</text><path d="M350 140V164" stroke="#a8bbc3" strokeWidth="1.7" markerEnd={`url(#${prefix}-arrow)`}/><rect x="253" y="174" width="194" height="45" rx="9" fill="#e0f1ef"/><text x="350" y="201" textAnchor="middle" fill="#147971" fontSize="12">Sample collection</text></g>:stage===1?<g>{[0,1,2].map(i=><g key={i} transform={`translate(${249+i*77} 87)`}><rect x="-13" width="61" height="116" rx="9" fill="#fff" stroke="#dce7ea"/><text x="17" y="20" textAnchor="middle" fontSize="10" fill="#526b78">Group {i+1}</text><People x={5} y={45} count={2} columns={2}/><path d="M4 88h26" stroke={active} strokeWidth="2"/><circle cx="17" cy="88" r="5" fill="#fff" stroke={active} strokeWidth="2"/></g>)}<text x="350" y="232" textAnchor="middle" fontSize="10" fill="#526b78">Protocol-guided dosing and review</text></g>:stage===2?<g><rect x="247" y="74" width="205" height="145" rx="10" fill="#fff" stroke="#dce7ea"/><text x="350" y="98" textAnchor="middle" fill="#193947" fontSize="12" fontWeight="600">Illustrative study arm</text><People x={300} y={125} count={8} columns={4}/><text x="350" y="199" textAnchor="middle" fill="#526b78" fontSize="10">One possible design</text></g>:stage===3?<g><text x="350" y="60" textAnchor="middle" fill="#526b78" fontSize="10">Random assignment in this example</text>{[0,1].map(i=><g key={i}><rect x="237" y={74+i*84} width="225" height="71" rx="9" fill="#fff" stroke="#dce7ea"/><text x="250" y={94+i*84} fill="#193947" fontSize="11" fontWeight="600">{i===0?'Study treatment':'Comparator'}</text><People x={262} y={116+i*84} count={6} columns={6} color={i===0?active:'#66788e'}/></g>)}</g>:<g><text x="350" y="79" textAnchor="middle" fill="#193947" fontSize="12" fontWeight="600">Follow-up after approval</text><path d="M254 134H444" stroke="#a8bbc3" strokeWidth="2"/>{[0,1,2,3].map(i=><g key={i}><circle cx={261+i*59} cy="134" r="8" fill={i<=step?'#088b83':'#fff'} stroke={active} strokeWidth="1.5"/><path d={`M${261+i*59} 148v13`} stroke="#a8bbc3"/><text x={261+i*59} y="179" textAnchor="middle" fill="#526b78" fontSize="10">Visit {i+1}</text></g>)}<text x="350" y="214" textAnchor="middle" fill="#526b78" fontSize="10">Timing depends on the protocol</text></g>}
    <g>{(stage===0?['Drug behavior','Biological response']:stage===1?['Tolerability','Dosing observations']:stage===2?['Activity measures','Safety observations']:stage===3?['Measures in both arms','Safety observations']:['Safety information','Effectiveness data']).map((label,i)=><g key={label} opacity={step>=2?1:.45} className="pa-diagram-observation"><rect x="527" y={77+i*70} width="160" height="56" rx="8" fill="#fff" stroke="#dce7ea"/><path d={`M540 ${93+i*70}h10m-10 7h19m-19 7h14`} stroke={active} strokeWidth="2" strokeLinecap="round"/><text x="540" y={122+i*70} fill="#193947" fontSize="10">{label}</text></g>)}<text x="607" y="231" textAnchor="middle" fill={step===3?active:'#526b78'} fontSize="11" fontWeight={step===3?700:400}>{step===3?'Review the evidence':'Record observations'}</text></g>
    <circle className="pa-flow-dot" cx={step===0?102:step===1?350:607} cy="269" r="4" fill={active}/>
  </svg>;
}

function Quiz({onReview}:{onReview:(phase:number)=>void}) {
  const [question, setQuestion] = useState(0);
  const [answers,setAnswers] = useState<(number|null)[]>(() => PHASE_QUIZ.map(() => null));
  const [finished,setFinished] = useState(false);
  const feedback = useRef<HTMLDivElement>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const current = PHASE_QUIZ[question];
  const chosen = answers[question];
  const score = answers.reduce<number>((total,answer,i) => total + (answer===PHASE_QUIZ[i].answer?1:0),0);
  const reset=()=>{setAnswers(PHASE_QUIZ.map(()=>null));setQuestion(0);setFinished(false);requestAnimationFrame(()=>heading.current?.focus())};
  return <section className="panel pa-quiz" aria-labelledby="pa-quiz-heading"><header className="panel-heading"><h2 id="pa-quiz-heading"><CircleHelp size={18}/> Check your understanding</h2><span className="pa-caption">5 questions · no time limit</span></header>
    {finished?<div className="pa-quiz-result"><div className="pa-result-icon"><BookOpen size={25}/></div><h3 ref={heading} tabIndex={-1}>You’ve completed the knowledge check.</h3><p><strong>{score} of {PHASE_QUIZ.length}</strong> correct. Revisit any stage whenever you need a refresher.</p><button className="btn secondary" onClick={reset}><RotateCcw size={15}/> Try again</button></div>:<div className="pa-quiz-body"><div className="pa-quiz-progress" aria-label={`Question ${question+1} of ${PHASE_QUIZ.length}`}>{PHASE_QUIZ.map((_,i)=><span key={i} className={i===question?'current':answers[i]!==null?'answered':''}/>)}</div><span className="pa-eyebrow">QUESTION {question+1} OF {PHASE_QUIZ.length}</span><h3 ref={heading} tabIndex={-1}>{current.question}</h3><div className="pa-quiz-options">{current.options.map((option,i)=><button key={option} className={`pa-quiz-option ${chosen===i?'selected':''} ${chosen!==null&&i===current.answer?'correct':''}`} disabled={chosen!==null} onClick={()=>{setAnswers(previous=>previous.map((a,index)=>index===question?i:a));requestAnimationFrame(()=>feedback.current?.focus())}}><span>{String.fromCharCode(65+i)}</span>{option}{chosen!==null&&i===current.answer?<Check size={17}/>:null}</button>)}</div>
      {chosen!==null?<div className={`pa-feedback ${chosen===current.answer?'correct':''}`} ref={feedback} tabIndex={-1} role="status"><strong>{chosen===current.answer?'That’s right.':'A useful distinction.'}</strong> {current.explanation}<div className="pa-feedback-actions">{current.phase!==null?<button className="text-btn" onClick={()=>onReview(current.phase!)}>Revisit Phase {PHASE_LESSONS[current.phase!].roman} <ArrowUpRight size={14}/></button>:<span/>}<button className="btn primary" onClick={()=>{if(question===PHASE_QUIZ.length-1)setFinished(true);else setQuestion(q=>q+1);requestAnimationFrame(()=>heading.current?.focus())}}>{question===PHASE_QUIZ.length-1?'See result':'Next question'}<ArrowRight size={15}/></button></div></div>:<p className="pa-caption pa-quiz-hint">Choose an answer to see an explanation.</p>}
      <button className="text-btn pa-reset-quiz" onClick={reset}><RotateCcw size={13}/> Reset quiz</button></div>}
  </section>;
}

export function PhaseAcademy({rows,onStudy}:{rows:Study[];onStudy?:(id:string)=>void}) {
  const [selected,setSelected] = useState(1);
  const [step,setStep] = useState(0);
  const [playing,setPlaying] = useState(false);
  const [speed,setSpeed] = useState(1);
  const reducedMotion = useReducedMotion();
  const prefix = useId().replaceAll(':','');
  const tabs = useRef<(HTMLButtonElement|null)[]>([]);
  const phase = PHASE_LESSONS[selected];
  const examples = useMemo(()=>rows.filter(row=>phaseKeys(row.phase).includes(phase.id)).slice(0,3),[rows,phase.id]);
  const selectPhase=(index:number,focus=false)=>{setSelected(index);setStep(0);setPlaying(false);if(focus)tabs.current[index]?.focus()};
  useEffect(()=>{if(reducedMotion)setPlaying(false)},[reducedMotion]);
  useEffect(()=>{
    if(!playing||reducedMotion)return;
    const timer=window.setTimeout(()=>{
      if(step>=2)setPlaying(false);
      setStep(Math.min(step+1,3));
    },4000/speed);
    return()=>window.clearTimeout(timer);
  },[playing,speed,reducedMotion,step]);
  const handleTabKey=(event:KeyboardEvent<HTMLButtonElement>,index:number)=>{
    let next=index;
    if(event.key==='ArrowRight')next=(index+1)%PHASE_LESSONS.length;
    else if(event.key==='ArrowLeft')next=(index+PHASE_LESSONS.length-1)%PHASE_LESSONS.length;
    else if(event.key==='Home')next=0;
    else if(event.key==='End')next=PHASE_LESSONS.length-1;
    else return;
    event.preventDefault();selectPhase(next,true);
  };
  const source=PHASE_SOURCES[phase.source as keyof typeof PHASE_SOURCES];
  return <div className={`phase-academy ${reducedMotion?'pa-reduced-motion':''}`}>
    <section className="pa-hero"><div><span className="pa-eyebrow"><BookOpen size={14}/> PHASE ACADEMY</span><h2>One question leads<br/>to the next.</h2><p>Explore how clinical research changes from early exploration to learning after approval.</p><div className="pa-hero-meta"><span>5 learning stages</span><i/><span>Interactive guide</span><i/><span>No model required</span></div></div><div className="pa-hero-aside" aria-hidden="true"><span className="pa-hero-orbit"><FlaskConical size={44}/></span><span className="pa-orbit-label one">ASK</span><span className="pa-orbit-label two">OBSERVE</span><span className="pa-orbit-label three">LEARN</span></div></section>
    <div className="pa-stage-heading"><h3>The clinical research journey</h3><span>Choose a stage to explore</span></div>
    <div className="pa-stage-tabs" role="tablist" aria-label="Clinical trial phases">{PHASE_LESSONS.map((lesson,index)=>{const Icon=stageIcons[index];return <button type="button" role="tab" key={lesson.id} id={`${prefix}-tab-${lesson.id}`} aria-selected={selected===index} aria-controls={`${prefix}-lesson`} tabIndex={selected===index?0:-1} ref={node=>{tabs.current[index]=node}} onKeyDown={event=>handleTabKey(event,index)} onClick={()=>selectPhase(index)} className={`pa-stage-tab ${selected===index?'active':''} ${index===0?'optional':''}`}><span className="pa-stage-icon"><Icon size={20}/></span><span><strong>Phase {lesson.roman}{index===0?<em>Optional</em>:null}</strong><small>{lesson.title}</small></span><ChevronRight className="pa-stage-chevron" size={15}/></button>})}</div>
    <div className="pa-lesson-layout" id={`${prefix}-lesson`} role="tabpanel" aria-labelledby={`${prefix}-tab-${phase.id}`} tabIndex={0}>
      <section className="panel pa-lesson"><div className="pa-lesson-top"><span className="pa-phase-label">PHASE {phase.roman}</span><span className="pa-focus">{phase.focus}</span></div><h3>{phase.question}</h3><p>{phase.purpose}</p><div className="pa-scale"><Users size={19}/><div><small>Illustrative scale</small><strong>{phase.scale}</strong><p>{phase.scaleNote}</p></div></div><div className="pa-oversight"><ShieldCheck size={18}/><div><strong>Participant protection throughout</strong><p>Protocol review, informed consent and safety monitoring remain part of clinical research.</p></div></div><a className="pa-source-link" href={source.url} target="_blank" rel="noreferrer">{source.label}<ArrowUpRight size={14}/></a></section>
      <section className="panel pa-visual-panel"><header className="pa-visual-heading"><div><span className="pa-eyebrow">SEE THE STUDY STRUCTURE</span><h3>{phase.title}, step by step</h3></div><span className="pa-concept-label">Conceptual illustration</span></header><div className="pa-diagram-scroll" tabIndex={0} role="region" aria-label="Conceptual study illustration; scroll horizontally on small screens"><Diagram phase={phase} step={step} prefix={prefix}/></div><p className="pa-diagram-note">Symbols are illustrative; they do not represent actual enrollment or patient outcomes.<span className="pa-scroll-hint"> Swipe or scroll horizontally to explore the diagram.</span></p><div className="pa-step-track" aria-label="Illustration steps">{STEP_NAMES.map((label,index)=><button key={label} aria-current={step===index?'step':undefined} className={step===index?'active':''} onClick={()=>{setStep(index);setPlaying(false)}}><span>{index+1}</span>{label}</button>)}</div><div className="pa-step-description" aria-live={playing?'off':'polite'}><span>{String(step+1).padStart(2,'0')}</span><p>{phase.steps[step]}</p></div><div className="pa-controls"><button className="btn primary" disabled={reducedMotion} title={reducedMotion?'Automatic playback is disabled by your reduced-motion setting':undefined} onClick={()=>{if(step===3)setStep(0);setPlaying(v=>!v)}}>{playing?<Pause size={15}/>:<Play size={15}/>} {playing?'Pause':'Play'}</button><button className="btn secondary" onClick={()=>{setPlaying(false);setStep(current=>(current+1)%4)}}><SkipForward size={15}/> Step</button><button className="icon-btn" aria-label="Reset illustration" title="Reset illustration" onClick={()=>{setStep(0);setPlaying(false)}}><RotateCcw size={17}/></button><label className="pa-speed">Speed<select aria-label="Animation speed" value={speed} onChange={event=>setSpeed(Number(event.target.value))} disabled={reducedMotion}><option value={0.5}>0.5×</option><option value={1}>1×</option><option value={2}>2×</option></select></label></div>{reducedMotion?<p className="pa-motion-note">Reduced motion is on. Use Step or choose a numbered step.</p>:<p className="pa-motion-note">Playback stops after Review. All controls work with a keyboard.</p>}</section>
    </div>
    <Notice>Phases describe research objectives, not a guarantee of safety, benefit or approval. This guide explains drug-development concepts; individual protocols can differ.</Notice>
    <div className="pa-context-grid"><section className="panel pa-examples"><header className="panel-heading"><h2>Connect the idea to a study</h2><span className="pa-caption">Loaded workspace records</span></header><p className="pa-section-intro">Matching the recorded phase field for Phase {phase.roman}. These records illustrate labels, not outcomes.</p>{examples.length?<div className="pa-example-list">{examples.map(row=><article key={row.nct_id}><div><span className="pa-example-id">{row.nct_id}</span><span className="phase">{nice(row.phase)}</span></div><h3>{row.title}</h3><footer><span>Enrollment: {number(row.enrollment)}</span>{onStudy?<button className="text-btn" onClick={()=>onStudy(row.nct_id)}>Open study <ArrowUpRight size={14}/></button>:<span className="pa-caption">Context record</span>}</footer></article>)}</div>:<div className="pa-no-example"><BookOpen size={24}/><strong>No matching record in this workspace</strong><p>The lesson works independently of your data. Import a dataset containing this phase to see contextual examples.</p></div>}</section><section className="panel pa-labels"><header className="panel-heading"><h2>When labels don’t fit one stage</h2></header><div className="pa-label-item"><span className="pa-label-badge">I / II</span><div><h3>Combined phases</h3><p>One protocol can combine objectives, such as dose finding and preliminary activity. Keep the recorded combined label when interpreting a study.</p><a href={PHASE_SOURCES.combined.url} target="_blank" rel="noreferrer">Read the NCI definition <ArrowUpRight size={13}/></a></div></div><div className="pa-label-item"><span className="pa-label-badge neutral">N/A</span><div><h3>Not applicable</h3><p>Studies such as device or behavioral trials may not use FDA-defined drug phases. N/A is different from an unknown or missing phase.</p><a href={PHASE_SOURCES.labels.url} target="_blank" rel="noreferrer">Explore registry terminology <ArrowUpRight size={13}/></a></div></div><p className="pa-early-note"><strong>Early Phase 1?</strong> Registries may use this label for what was previously called Phase 0.</p></section></div>
    <Quiz onReview={index=>{selectPhase(index);tabs.current[index]?.scrollIntoView({behavior:reducedMotion?'auto':'smooth',block:'center'});tabs.current[index]?.focus({preventScroll:true})}}/>
    <footer className="pa-reading"><div><BookOpen size={18}/><span>Continue learning from primary sources</span></div><nav aria-label="Phase Academy sources">{Object.entries(PHASE_SOURCES).map(([key,item])=><a key={key} href={item.url} target="_blank" rel="noreferrer">{item.label}<ArrowUpRight size={12}/></a>)}</nav><p>Educational summaries checked October 2026. This guide does not assign regulatory phases or provide treatment advice.</p></footer>
  </div>;
}
