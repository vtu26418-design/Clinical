import {Canvas} from '@react-three/fiber';
import {ScientificWorld,type ScientificWorldProps} from './ScientificWorld';
export default function StudioCanvas(props:ScientificWorldProps){return <Canvas orthographic camera={{position:[0,0,15],zoom:60,near:0.1,far:60}} frameloop={props.running?'always':'demand'} dpr={props.settings.detail==='low'?1:[1,1.5]} gl={{antialias:props.settings.detail!=='low',preserveDrawingBuffer:true,powerPreference:'low-power'}}><ScientificWorld {...props}/></Canvas>}
