import type {ScienceDocument,ScienceScene,ScienceStep} from './types';
export const sceneNames:Record<ScienceScene,string>={neurons:'Neurons',molecule:'Molecule',dna:'DNA',pipeline:'Pipeline'};
export const defaultSettings:ScienceDocument['settings']={accent:'#63e5d8',background:'midnight',detail:'standard',speed:1,show_labels:true,camera:'front',voice_uri:'',voice_rate:1};
const steps:Record<ScienceScene,Array<[string,string,ScienceStep['focus'],string[]]>>={
 neurons:[['Signal travels along the axon','In this simplified neuron, an electrical signal propagates along the axon. Myelin supports rapid transmission between exposed nodes.','input',['Dendrites','Cell body (soma)','Axon','Myelin sheath']],['Signal crosses the synapse','At the terminal, vesicles release neurotransmitters. They cross the synaptic cleft and bind to receptors on the next cell.','transfer',['Synaptic terminal','Vesicles','Synaptic cleft','Receptors']],['The next cell responds','Receptor activation changes the receiving cell’s activity. Whether it fires depends on the combined inputs it receives.','output',['Receiving neuron','Receptors']]],
 molecule:[['Explore molecular structure','Atoms and bonds are arranged as a stylized molecular illustration. This is not a specific compound or measured structure.','overview',['Illustrative atoms','Illustrative bonds']],['Inspect an interaction','The moving highlight illustrates an interaction pathway; it does not simulate binding, potency or treatment effects.','processing',['Interaction illustration']],['Return to source evidence','Use source experiments and validated measurements to assess a particular molecule. This illustration contains no assay results.','output',['Source evidence required']]],
 dna:[['Explore the double helix','Two backbones and connecting base-pair symbols show the organization of a DNA double helix.','input',['Backbone','Base-pair symbols']],['Follow the sequence','The moving highlight guides attention along the helix. The symbols do not encode a patient or trial sequence.','transfer',['Illustrative sequence']],['Connect to the research question','Use measured genomic evidence for biological conclusions. The shape alone does not support a clinical prediction.','output',['Conceptual DNA']]],
 pipeline:[['Review the inputs','Source records enter a defined processing workflow. Check the actual source and the fields available at the prediction cutoff.','input',['Source records','Available fields']],['Apply the recorded method','A bounded processing stage represents the selected model or method. Motion does not describe its architecture or measured performance.','processing',['Processing','Recorded method']],['Inspect the output and evidence','Read the returned values, provenance and evaluation evidence. An illustration cannot establish model accuracy or causality.','output',['Output','Evaluation evidence']]],
};
export function createTemplate(scene:ScienceScene='neurons'):ScienceDocument{return {version:1,title:scene==='neurons'?'Neural signaling · explainer':`${sceneNames[scene]} · explainer`,source_notes:'',scene,steps:steps[scene].map(([title,caption,focus,labels],i)=>({id:`step-${i+1}`,title,caption,narration:caption,focus,labels})),settings:{...defaultSettings}}}
/** Preserve supplied notes literally; no invented summary or scientific claims. */
export function fromSourceNotes(title:string,notes:string,scene:ScienceScene):ScienceDocument {
 const source=notes.slice(0,32000),chunks:string[]=[];
 for(const paragraph of source.split(/\n\s*\n/).filter(part=>part.trim())){for(let i=0;i<paragraph.length&&chunks.length<12;i+=1400)chunks.push(paragraph.slice(i,i+1400))}
 return {...createTemplate(scene),title:title.trim().slice(0,160)||'Source notes · explanation',source_notes:source,steps:(chunks.length?chunks:['Add a caption from your source notes.']).map((caption,i)=>{const heading=caption.split('\n')[0];const focus:ScienceStep['focus']=/^(source|context|input)/i.test(heading)?'input':/^(recorded method|processing|model)/i.test(heading)?'processing':/^(returned result|output|interpretation)/i.test(heading)?'output':'overview';return {id:`source-${i+1}`,title:heading.length<=120?heading:`Source excerpt ${i+1}`,caption,narration:caption,focus,labels:[]}})};
}
export function chooseSceneFromEvidence(text:string):ScienceScene {
 if(/^Context:\s*dataset\b/im.test(text))return 'pipeline';
 if(/^Context:\s*study\b/im.test(text)){
  const topic=text.split(/\n\s*\n/).find(part=>/^Context:\s*study\b/im.test(part))||'';
  text=topic.replace(/^Context:\s*study\b/im,'');
 }
 if(/\b(neuron\w*|neural|brain|neurolog\w*|synap\w*|axon\w*|dendrit\w*)\b/i.test(text))return 'neurons';
 if(/\b(genom\w*|gene|genes|genetic\w*|sequencing|dna|rna)\b/i.test(text))return 'dna';
 if(/\b(drug\w*|molecul\w*|compound\w*|pharmac\w*|intervention\s*:\s*drug)\b/i.test(text))return 'molecule';
 return 'pipeline';
}
export function contextualTemplate(evidence?:{title:string;notes:string}):ScienceDocument {
 return evidence?.notes.trim()?fromSourceNotes(evidence.title,evidence.notes,chooseSceneFromEvidence(evidence.notes)):createTemplate('pipeline');
}
export function sceneDisclaimer(scene:ScienceScene){return scene==='neurons'?'Simplified neural signaling. For non-biology topics, neurons are a teaching metaphor; they do not describe the model architecture.':scene==='pipeline'?'Illustrative processing flow. Read actual model methods and returned values alongside the scene.':'Conceptual scientific illustration; no measured molecular or genomic structure.'}
