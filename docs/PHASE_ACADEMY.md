# Phase Academy

Phase Academy is the built-in educational screen. It runs entirely in the browser and works without an API, model artifact, or dataset. No network request occurs until a reader follows an external source link.

## Interface

```tsx
import {PhaseAcademy} from './components/PhaseAcademy';

<PhaseAcademy rows={rows} onStudy={id => openStudy(id)} />
```

Props are `{ rows: Study[]; onStudy?: (id: string) => void }`. Study examples come only from the supplied rows' recorded `phase` fields. The component does not infer a phase from a title, enrollment, prediction, or diagram. It displays up to three matching rows and preserves their recorded labels. Combined phases may appear in both relevant lessons. Empty datasets show an honest no-record state. Fixture data remains fixture data; the application-level fixture notice must remain visible.

Owned files:

- `frontend/src/components/PhaseAcademy.tsx`: screen, conceptual SVG, motion controls, study context, five-question quiz.
- `frontend/src/components/phaseAcademy.css`: isolated responsive styles and motion overrides.
- `frontend/src/phaseContent.ts`: educational content, primary source URLs, quiz, registry label matching.

## Learning and motion

Select an optional Phase 0 or Phase I–IV tab. Arrow keys move between tabs; Home/End selects the first/last tab. Each stage has four illustration steps. Play advances every four seconds at 1× and stops at Review; 0.5× and 2× change this interval. Pause preserves the current step. Step advances manually and wraps after Review. Reset returns the illustration to the first step without changing the selected phase or quiz.

The operating-system `prefers-reduced-motion` setting disables automatic playback, speed changes and CSS motion. Manual steps remain available. A preference change while playing stops playback. The illustration is an accessible SVG with a phase- and step-specific title/description. Controls are native buttons/selects; focus follows quiz feedback and questions. Narration remains available as ordinary text during playback, without repeated live announcements. Quiz answers lock after selection, show the correct answer and explanation, and can be reset.

The figures are conceptual compositions, not generated clinical records. Participant symbols do not encode counts, outcomes or probabilities. Phase III shows an example two-arm structure without a winning arm. Phase I does not prescribe escalation or a dose. The guide never assumes that a drug will progress, become approved, or benefit participants. Enrollment scale is labeled illustrative.

## Sources

Primary pages were checked on 2026-10-07. Content is concise paraphrase, with source links in the lesson and reading footer. The app's learning model is educational and separate from the experimental phase classifier.

| Source | Use |
| --- | --- |
| [FDA: Step 3, Clinical Research](https://www.fda.gov/patients/drug-development-process/step-3-clinical-research) | Phase I–IV purpose and qualified enrollment examples |
| [NCI: DTC clinical-trial FAQs](https://dctd.cancer.gov/programs/dtc/about/about-dtc-clinical-trials) | Phase 0 exploratory purpose |
| [NCI: How Do Clinical Trials Work?](https://www.cancer.gov/research/participate/clinical-trials/how-trials-work) | Study design, random assignment, oversight |
| [NCI: Phase 1/Phase 2 clinical trial](https://www.cancer.gov/publications/dictionaries/cancer-terms/def/phase-1-phase-2-clinical-trial) | Combined phase explanation |
| [NIH NCATS: Phases of Clinical Trials](https://toolkit.ncats.nih.gov/glossary/phases-of-clinical-trials/) | Early Phase 1 and N/A registry terminology |

## Quick verification

1. Open Academy with empty rows and with a dataset containing ordinary and combined phase labels.
2. Select all five tabs using mouse and keyboard; verify each diagram changes.
3. Run Play to Review, change speed, pause, step, and reset.
4. Enable reduced motion in the browser/OS; verify playback is disabled and Step works.
5. Answer all five quiz questions; verify feedback, final score and reset.
6. Open a contextual study and confirm the callback receives its original NCT ID.
7. Inspect at narrow mobile width: phase tabs scroll horizontally; lesson content and controls remain usable.
