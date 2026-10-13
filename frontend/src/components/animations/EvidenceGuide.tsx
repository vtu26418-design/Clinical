import {ScenePanel} from '../three/ScenePanel';
import type {ScenePanelProps} from '../three/types';
import './guidedEvidence.css';
/** One scene on the active screen; existing analytical views remain its exact 2D evidence. */
export function GuidedEvidence(props:ScenePanelProps) {
 return <div className="cti-guided-evidence"><ScenePanel {...props}/></div>;
}
