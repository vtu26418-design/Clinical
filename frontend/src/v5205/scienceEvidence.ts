import type {Dataset,Detail,Study} from '../types';

function value(input:unknown){return input===null||input===undefined||input===''?'Not reported':typeof input==='number'&&!Number.isFinite(input)?'Unavailable':String(input)}
/** Only source/returned values become captions; no invented statistics or biology. */
export function scienceEvidence(dataset:Dataset,study?:Study,detail?:Detail|null){
 const current=detail?.study.nct_id===study?.nct_id?detail:null;
 const selected=current?.study||study;
 const source=['Source',`Dataset: ${dataset.name}`,`Dataset ID: ${dataset.id}`,`Records: ${dataset.row_count}`,`Source: ${dataset.source}`,
  `Source SHA-256: ${value(dataset.sha256)}`,dataset.is_fixture?'Software fixture; no scientific prediction is supported.':'Public or imported source records; current registry fields may be updated after study start.'];
 if(!selected)return {title:'Dataset processing and evidence',notes:['Context: dataset',source.join('\n'),
  'Recorded method\nSelect a study to connect this explanation to its protocol fields and approved saved model.',
  'Returned result\nDataset counts describe source records, not the number used to fit a model. No selected-study prediction is supplied.',
  'Interpretation\nThe processing scene is an illustration. Model accuracy requires labelled held-out evaluation in Settings → Model quality.'].join('\n\n')};
 const prediction=current?.prediction;
 const method=['Recorded method',`PCI score: ${value(current?.pci.score)}`,`PCI category: ${value(current?.pci.category)}`,
  `Approved model ID: ${value(prediction?.approved_model_id)}`,`Model branch: ${value(prediction?.model_name)}`,`Run ID: ${value(prediction?.run_id)}`];
 const result=prediction?.status==='available'?['Returned result',`Predicted total duration (days): ${value(prediction.duration_days)}`,
  `Prolonged-duration probability: ${value(prediction.probability)}`,`Prediction scope: ${value(prediction.prediction_scope)}`]:
  ['Returned result',prediction?.reason||'No prediction has been loaded for this selected study.'];
 return {title:selected.title.slice(0,160),notes:[`Context: study\nTopic: ${selected.title}\n${selected.brief_summary?.slice(0,1000)||''}`,
  [...source,`Study ID: ${selected.nct_id}`,`Recorded phase: ${value(selected.phase)}`,`Status: ${value(selected.status)}`,
   `Start date as reported: ${value(selected.start_date)}`,`Completion date as reported: ${value(selected.completion_date)}`].join('\n'),
  method.join('\n'),result.join('\n'),
  'Interpretation\nBiological shapes are educational schematics, not measured anatomy or model architecture. Prolonged duration is not delay against a planned schedule. Registry snapshots do not establish pretrial validation; model explanations do not establish causality.'].join('\n\n')};
}
