import {Activity,BarChart3,BookOpen,BrainCircuit,Calculator,Clock,Database,FileText,FlaskConical,GitBranch,Home,Layers,MessageSquare,Network,Search,Settings,Shield,ShieldCheck,Sliders,Sparkles,Users,Zap} from 'lucide-react';

export const navigation = [
 ['overview','Overview',Home],['explorer','Studies',Search],['predict','Prediction Studio',Sparkles],
 ['protocols','Protocol Evidence',FileText],['digital-twin','Scenarios',GitBranch],['models','Models',Layers],
 ['assistant','Assistant',MessageSquare],['workspace','Settings',Settings],['science-studio','Science Studio',Sparkles],
 ['home','Research home',Home],['sources','Research sources',BookOpen],['library','Saved library',FileText],
 ['research-hub','Research Hub',Network],['complexity','Complexity Lab',BarChart3],['formula-studio','Formula Studio',Calculator],
 ['experiments','Experiments',FlaskConical],['validation-lab','Validation Lab',ShieldCheck],['academy','Phase Academy',BookOpen],
 ['phase-model','Phase Model',BrainCircuit],['data','Data Manager',Database],['ai-pipeline','AI Pipeline',Activity],
 ['trial-timeline','Trial Timeline',Clock],['xai','Explainability',Zap],['recruitment','Recruitment',Users],
 ['what-if','What-If Lab',Sliders],['fusion','Data Fusion',Layers],['roles','Access Control',Shield],
] as const;
export const coreRoutes = new Set(['overview','explorer','predict','protocols','digital-twin','models','assistant','workspace']);
export const evidenceRoutes = new Set(['ai-pipeline','trial-timeline','xai','recruitment','what-if','fusion','science-studio']);
export const titles:Record<string,string> = {
 overview:'Overview',home:'Research home',sources:'Research sources',library:'Saved library',predict:'Prediction Studio',
 protocols:'Protocol evidence',models:'Model registry',workspace:'Workspace settings','science-studio':'Science Studio',explorer:'Studies',complexity:'Protocol complexity',
 experiments:'Experiments',academy:'Phase Academy','phase-model':'Phase model',assistant:'Research assistant',data:'Data Manager',
 'research-hub':'Research Hub','digital-twin':'Scenarios','formula-studio':'Formula Studio','validation-lab':'Validation Lab',
 'ai-pipeline':'Model pipeline','trial-timeline':'Trial timeline',xai:'Explainability',recruitment:'Recruitment','what-if':'What-If Lab',
 fusion:'Data fusion',roles:'Access control',
};
