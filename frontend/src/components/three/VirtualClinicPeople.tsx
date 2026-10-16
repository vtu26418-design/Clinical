import {useLayoutEffect,useRef} from 'react';
import {useFrame} from '@react-three/fiber';
import {Group} from 'three';
import {advanceClinicTime,clinicWalk,type ClinicPoint,type ClinicStage} from './VirtualClinicMotion';
const skin='#c99977',ink='#263c3c',coat='#f6f5ed';
function Limb({length=0.34,color}:{length?:number;color:string}){return <mesh castShadow position={[0,-length/2,0]}><capsuleGeometry args={[0.065,length-0.13,5,10]}/><meshStandardMaterial color={color} roughness={0.85}/></mesh>}
const arrivals:Record<ClinicStage['zone'],ClinicPoint>={reception:[-2.7,0,1],screening:[-2,0,-0.45],exam:[0,0,-0.25],sample:[-2,0,-0.4],review:[1.9,0,-0.6],comparison:[1.7,0,0.9],followup:[2.6,0,1.6]};
export function VirtualClinicPerson({role,stage,running,speed}:{role:'patient'|'doctor'|'researcher';stage:ClinicStage;running:boolean;speed:number}){
 const root=useRef<Group>(null),head=useRef<Group>(null),leftArm=useRef<Group>(null),rightArm=useRef<Group>(null),leftElbow=useRef<Group>(null),rightElbow=useRef<Group>(null),leftLeg=useRef<Group>(null),rightLeg=useRef<Group>(null),leftKnee=useRef<Group>(null),rightKnee=useRef<Group>(null),time=useRef(0);
 const medical=role==='doctor',patient=role==='patient',shirt=medical?coat:patient?'#75928a':'#287b75',trouser=patient?'#c2ae8b':'#34474a';
 const target=arrivals[stage.zone],origin:ClinicPoint=patient?[target[0]-0.7,0,Math.min(2.3,target[2]+1.05)]:role==='doctor'?[-0.95,0,0.3]:stage.zone==='sample'?[-3.05,0,-1.1]:[2.9,0,-0.95];
 function pose(t:number){if(!root.current)return;const travel=patient?clinicWalk(origin,target,t):null,walking=travel?.walking??false,gait=walking?Math.sin(t*9)*0.44:0;
  root.current.position.set(...(travel?.position??origin));const partner:ClinicPoint=patient?(stage.zone==='review'?[2.9,0,-0.95]:stage.zone==='sample'?[-3.05,0,-1.1]:[-0.95,0,0.3]):target;root.current.rotation.y=walking?travel!.heading:role==='researcher'?Math.PI:Math.atan2(partner[0]-root.current.position.x,partner[2]-root.current.position.z);
  root.current.position.y=walking?Math.abs(Math.sin(t*9))*0.035:0;
  if(head.current){head.current.rotation.y=Math.sin(t*0.8)*0.07;head.current.rotation.x=!walking&&stage.action==='read'?0.16:0}
  if(leftLeg.current)leftLeg.current.rotation.x=gait;if(rightLeg.current)rightLeg.current.rotation.x=-gait;
  if(leftKnee.current)leftKnee.current.rotation.x=walking?Math.max(0,-gait)*0.8:0;if(rightKnee.current)rightKnee.current.rotation.x=walking?Math.max(0,gait)*0.8:0;
  if(leftArm.current)leftArm.current.rotation.x=walking?-gait*0.7:patient?-0.12:-0.38;
  if(rightArm.current){rightArm.current.rotation.x=walking?gait*0.7:medical?-0.45:stage.action==='sample'?-0.65:-0.38;rightArm.current.rotation.z=!walking&&medical?-0.32-Math.sin(t*1.9)*0.09:0}
  if(leftElbow.current)leftElbow.current.rotation.x=walking?-0.12:patient?-0.15:-0.9;
  if(rightElbow.current)rightElbow.current.rotation.x=walking?-0.12:medical?-0.55-Math.sin(t*1.9)*0.12:-0.85+Math.sin(t*2)*0.06;
 }
 useLayoutEffect(()=>{time.current=0;pose(0)},[stage.zone,stage.action,role]);
 useFrame((_,delta)=>{if(!running)return;time.current=advanceClinicTime(time.current,delta,true,speed);pose(time.current)});
 return <group ref={root}>
  <group position={[0,0.9,0]}><mesh castShadow position={[0,0.28,0]}><cylinderGeometry args={[0.19,medical?0.23:0.18,0.6,12]}/><meshStandardMaterial color={shirt} roughness={0.9}/></mesh>{medical&&<><mesh position={[0,0.33,0.19]}><boxGeometry args={[0.12,0.42,0.018]}/><meshStandardMaterial color="#67918d"/></mesh>{[-1,1].map(s=><mesh key={s} position={[s*0.105,0.31,0.2]} rotation={[0,0,s*0.18]}><boxGeometry args={[0.08,0.5,0.035]}/><meshStandardMaterial color={coat}/></mesh>)}<mesh position={[0.12,0.35,0.228]}><boxGeometry args={[0.065,0.09,0.018]}/><meshStandardMaterial color="#86aaa1"/></mesh></>}</group>
  <mesh position={[0,1.53,0]}><cylinderGeometry args={[0.075,0.08,0.15,10]}/><meshStandardMaterial color={skin}/></mesh>
  <group ref={head} position={[0,1.72,0]}><mesh castShadow scale={[0.84,1.08,0.9]}><sphereGeometry args={[0.18,18,14]}/><meshStandardMaterial color={skin} roughness={0.9}/></mesh><mesh position={[0,0.065,-0.014]} scale={[0.9,1,0.94]}><sphereGeometry args={[0.184,18,12,0,Math.PI*2,0,Math.PI*0.61]}/><meshStandardMaterial color={medical?'#435254':'#49392f'} roughness={1}/></mesh>{[-1,1].map(s=><group key={s}><mesh position={[s*0.062,0.015,0.147]}><sphereGeometry args={[0.014,8,6]}/><meshStandardMaterial color={ink}/></mesh><mesh position={[s*0.157,-0.015,0]} scale={[0.6,1,0.7]}><sphereGeometry args={[0.038,8,8]}/><meshStandardMaterial color={skin}/></mesh></group>)}<mesh position={[0,-0.014,0.168]} scale={[0.6,0.8,1]}><sphereGeometry args={[0.032,8,6]}/><meshStandardMaterial color={skin}/></mesh><mesh position={[0,-0.073,0.143]}><boxGeometry args={[0.05,0.009,0.012]}/><meshStandardMaterial color="#946a56"/></mesh>{role==='researcher'&&<mesh position={[0,0.07,-0.17]}><sphereGeometry args={[0.09,10,10]}/><meshStandardMaterial color="#49392f"/></mesh>}</group>
  {([-1,1] as const).map(s=><group key={s} ref={s<0?leftArm:rightArm} position={[s*0.255,1.43,0]} rotation={[0,0,s*0.06]}><Limb color={shirt}/><group ref={s<0?leftElbow:rightElbow} position={[0,-0.32,0]}><Limb length={0.3} color={medical?coat:skin}/><mesh castShadow position={[0,-0.32,0]} scale={[0.85,1.2,0.75]}><sphereGeometry args={[0.064,10,8]}/><meshStandardMaterial color={skin}/></mesh>{s===-1&&!patient&&<group position={[0,-0.33,0.08]} rotation={[-0.3,0,0]}><mesh><boxGeometry args={[0.21,0.28,0.025]}/><meshStandardMaterial color="#425957"/></mesh><mesh position={[0,0.005,0.016]}><boxGeometry args={[0.17,0.23,0.007]}/><meshStandardMaterial color="#f5f1e6"/></mesh></group>}{s===1&&role==='researcher'&&stage.zone==='sample'&&<mesh position={[0,-0.36,0.07]}><cylinderGeometry args={[0.025,0.025,0.15,8]}/><meshStandardMaterial color="#b9d3cd" transparent opacity={0.8}/></mesh>}</group></group>)}
  {([-1,1] as const).map(s=><group key={s} ref={s<0?leftLeg:rightLeg} position={[s*0.105,0.9,0]}><Limb length={0.42} color={trouser}/><group ref={s<0?leftKnee:rightKnee} position={[0,-0.4,0]}><Limb length={0.39} color={trouser}/><mesh castShadow position={[0,-0.37,0.06]}><boxGeometry args={[0.15,0.11,0.27]}/><meshStandardMaterial color={patient?'#f1eee4':'#253b3c'} roughness={0.85}/></mesh></group></group>)}
 </group>
}
