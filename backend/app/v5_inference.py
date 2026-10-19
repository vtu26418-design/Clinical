"""Approved, immutable, project-scoped research inference. No training is called here.

Only bundled release-pinned artifacts or completed local experiments may be
approved. Approval is an operational research review, never clinical validation.
Model deserialization occurs only after path, version and digest checks.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from .config import PROJECT_ROOT
from .services.data_service import json_clean, now

RESEARCH_WARNING = 'Research approval only; not clinical, regulatory or prospective validation.'
RETROSPECTIVE_WARNING = 'Retrospective snapshot: baseline feature availability is unverified; post-start registry updates can leak outcomes.'
MODEL_ID_PATTERN = r'^[a-zA-Z0-9_-]{1,100}$'
EXACT_DATE_PATTERN = r'\d{4}-\d{2}-\d{2}'
EXACT_TIMESTAMP_PATTERN = EXACT_DATE_PATTERN + r'(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d{1,9})?)?(?:Z|[+-]\d{2}:\d{2})?)?'


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _present(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {'unknown', 'not reported', 'nan'}
    return not pd.isna(value)


def _availability_timestamp(value, *, date_only=False):
    """Do not let permissive date parsing invent a day or an epoch unit."""
    pattern = EXACT_DATE_PATTERN if date_only else EXACT_TIMESTAMP_PATTERN
    if not isinstance(value, str) or not re.fullmatch(pattern, value.strip()):
        return pd.NaT
    return pd.to_datetime(value.strip(), utc=True, errors='coerce')


def _names(task):
    return ('phase_manifest.json', 'phase_models.joblib') if task == 'phase' else ('manifest.json', 'models.joblib')


def _training_source(manifest):
    """Preserve registered-data and CLI provenance without inventing an ID."""
    source = manifest.get('source_metadata', {})
    # HTTP training records the upload checksum as sha256; the CLI records the
    # input file checksum as source_sha256. The frozen starter also carries its
    # replayable canonical-file digest. These are declared source metadata, not
    # a fallback to an unrelated artifact/input-pipeline hash.
    checksum = next((source[key] for key in ('sha256', 'source_sha256', 'canonical_sha256') if key in source), None)
    return {'id':source.get('dataset_id'), 'name':source.get('dataset_name', source.get('source_name')),
            'sha256':checksum, 'row_count':manifest.get('cohort', {}).get('input_rows')}


def _branch(manifest, task):
    models = manifest.get('models', {})
    if task == 'phase':
        return manifest.get('recommended_model')
    config = manifest.get('config', {})
    if config.get('enable_design_models'):
        # The frozen MAE protocol selects duration and risk independently. A
        # tie-winning regression component must not replace its risk component.
        if config.get('duration_selection_metric') == 'mae' and 'design_task_selected' in models:
            return 'design_task_selected'
        return manifest.get('recommended_duration_model')
    if config.get('enable_accuracy_models') and 'accuracy_task_selected' in models:
        return 'accuracy_task_selected'
    if 'duration_selection_metric' in config:
        return manifest.get('recommended_duration_model')
    # Legacy deterministic validation-only duration objective. Test metrics never select.
    candidates = [(name, value.get('metrics', {}).get('validation', {}).get('regression', {}).get('mae'))
                  for name, value in models.items()]
    candidates = [(name, score) for name, score in candidates if _finite(score)]
    return min(candidates, key=lambda pair: pair[1])[0] if candidates else None


def _input_mode(manifest, branch, seen=None):
    """Resolve the actual consumed modalities of independently selected tasks."""
    seen=set() if seen is None else set(seen)
    if branch in seen:
        raise HTTPException(409, 'Saved composite model metadata contains a cycle.')
    seen.add(branch)
    meta=manifest.get('models', {}).get(branch)
    if not isinstance(meta, dict):
        raise HTTPException(409, 'Saved composite component metadata is missing.')
    mode=meta.get('input_mode', 'multimodal')
    if mode!='composite':
        if mode not in {'baseline','text','structured','multimodal'}:
            raise HTTPException(409, 'Saved model input mode is unsupported.')
        return mode
    selection=meta.get('selection', {})
    modes={_input_mode(manifest, selection.get(key), seen) for key in ('regressor_component','classifier_component')}
    if 'multimodal' in modes or {'text','structured'} <= modes:return 'multimodal'
    return 'text' if 'text' in modes else 'structured' if 'structured' in modes else 'baseline'


def _explicit_input_requirement(features):
    if not isinstance(features, dict):
        raise HTTPException(409, 'Saved model input feature metadata is invalid.')
    fields = {}
    for kind in ('numeric', 'categorical', 'text'):
        values = features.get(kind, [])
        if not isinstance(values, (list, tuple)) or any(not isinstance(name, str) or not name for name in values):
            raise HTTPException(409, 'Saved model input feature metadata is invalid.')
        fields[kind] = list(values)
    structured, narrative = bool(fields['numeric'] or fields['categorical']), bool(fields['text'])
    mode = 'multimodal' if structured and narrative else 'structured' if structured else 'text' if narrative else 'baseline'
    return {'mode': mode, 'fields': fields, 'explicit': True}


def _input_requirements(manifest, branch, seen=None):
    """Return each selected task's actual schema, without broadening it."""
    seen = set() if seen is None else set(seen)
    if branch in seen:
        raise HTTPException(409, 'Saved composite model metadata contains a cycle.')
    seen.add(branch)
    meta = manifest.get('models', {}).get(branch)
    if not isinstance(meta, dict):
        raise HTTPException(409, 'Saved model component metadata is missing.')
    tasks = meta.get('task_input_features')
    if tasks is not None:
        if not isinstance(tasks, dict) or not all(task in tasks for task in ('regressor', 'classifier')):
            raise HTTPException(409, 'Saved model task input feature metadata is invalid.')
        return [_explicit_input_requirement(tasks[task]) for task in ('regressor', 'classifier')]
    mode = meta.get('input_mode', 'multimodal')
    if mode == 'composite':
        selection = meta.get('selection', {})
        return [requirement for key in ('regressor_component', 'classifier_component')
                for requirement in _input_requirements(manifest, selection.get(key), seen)]
    if mode not in {'baseline', 'structured', 'text', 'multimodal'}:
        raise HTTPException(409, 'Saved model input mode is unsupported.')
    if meta.get('input_features') is not None:
        return [_explicit_input_requirement(meta['input_features'])]
    if mode == 'baseline':
        features = {}
    elif branch == 'accuracy_phase_shrinkage':
        features = {'categorical': ['phase']}
    else:
        features = manifest.get('features', {})
    requirement = _explicit_input_requirement(features)
    requirement['explicit'] = False
    requirement['mode'] = mode
    for kind in ('numeric', 'categorical', 'text'):
        if not ((kind == 'text' and mode in {'text', 'multimodal'}) or (kind != 'text' and mode in {'structured', 'multimodal'})):
            requirement['fields'][kind] = []
    return [requirement]


def _consumed_features(requirements):
    return list(dict.fromkeys(name for requirement in requirements
                             for fields in requirement['fields'].values() for name in fields))


def _gates(manifest, task, branch):
    errors = []
    from src.clinical_trial_intelligence.research import ARTIFACT_VERSION as DURATION_VERSION
    from src.clinical_trial_intelligence.phase_model import ARTIFACT_VERSION as PHASE_VERSION
    if manifest.get('status') != 'completed' or manifest.get('task') != task or not manifest.get('run_id'):
        errors.append('A completed local manifest with the correct task and run identifier is required.')
    if manifest.get('artifact_version') != (PHASE_VERSION if task == 'phase' else DURATION_VERSION):
        errors.append('Artifact version is incompatible with this server.')
    source = manifest.get('source_metadata', {})
    if source.get('is_fixture') or source.get('fixture'):
        errors.append('Software fixtures cannot be approved as research models.')
    for name, value in [('training dataset hash', _training_source(manifest)['sha256']), ('pipeline hash', manifest.get('pipeline_source_sha256')),
                        ('training input hash', manifest.get('input_sha256'))]:
        if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
            errors.append(f'Missing valid {name}.')
    metrics = manifest.get('models', {}).get(branch, {}).get('metrics', {})
    for split in ('validation', 'test'):
        values = metrics.get(split, {})
        sample_count = values.get('n', manifest.get('splits', {}).get(split, {}).get('rows'))
        if not _finite(sample_count) or sample_count < 1:
            errors.append(f'{split} requires actual held-out observations.')
        scores = ([values.get('macro_f1'), values.get('accuracy')] if task == 'phase' else
                  [values.get('regression', {}).get('mae'), values.get('regression', {}).get('rmse'), values.get('classification', {}).get('brier')])
        if not all(_finite(score) for score in scores):
            errors.append(f'{split} requires finite task metrics; undefined optional AUROC/R² may remain null.')
    return errors


class ApprovedModelRegistry:
    def __init__(self, store, catalog_path=None):
        self.store = store
        self.catalog_path = Path(catalog_path or PROJECT_ROOT / 'examples/approved-models-v5.json')
        for statement in (
            'CREATE TABLE IF NOT EXISTS v5_model_approvals (project_id VARCHAR(64) NOT NULL,model_id VARCHAR(100) NOT NULL,payload TEXT NOT NULL,PRIMARY KEY(project_id,model_id))',
            'CREATE TABLE IF NOT EXISTS v5_active_models (project_id VARCHAR(64) NOT NULL,task VARCHAR(20) NOT NULL,model_id VARCHAR(100) NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(project_id,task))',
            'CREATE TABLE IF NOT EXISTS v5_inference_batches (id VARCHAR(64) PRIMARY KEY,project_id VARCHAR(64) NOT NULL,dataset_id VARCHAR(80) NOT NULL,user_id VARCHAR(64) NOT NULL,created_at TEXT NOT NULL,payload TEXT NOT NULL)',
            'CREATE INDEX IF NOT EXISTS v5_inference_scope ON v5_inference_batches(project_id,dataset_id,created_at)',
        ):
            store.execute(statement)

    def _approval(self, project_id, model_id):
        rows = self.store.execute('SELECT payload FROM v5_model_approvals WHERE project_id=:project AND model_id=:model',
                                  {'project':project_id, 'model':model_id}, True)
        return json.loads(rows[0]['payload']) if rows else None

    def _bundle_entries(self):
        try:
            return json.loads(self.catalog_path.read_text(encoding='utf-8')).get('models', [])
        except (OSError, ValueError, TypeError):
            return []

    def _inspect(self, project_id, registry, model_id):
        entry = next((value for value in self._bundle_entries() if value.get('id') == model_id), None)
        approval, run = None, None
        if entry:
            task = entry.get('task')
            if task not in {'duration', 'phase'}:
                raise HTTPException(409, 'Bundled model task is incompatible.')
            relative = Path(entry.get('directory', ''))
            folder = PROJECT_ROOT / relative
            if relative.is_absolute() or folder.is_symlink() or folder.resolve().parent != (PROJECT_ROOT/'examples').resolve():
                raise HTTPException(409, 'Bundled artifact path failed the trusted release check.')
            approval = entry.get('approval', {})
            if approval.get('scope') != 'research_only':
                raise HTTPException(409, 'Bundled artifact lacks a research release approval.')
            expected = entry
        elif re.fullmatch(r'project-[a-f0-9]{32}', model_id):
            run = registry.get_experiment(model_id[len('project-'):])
            if run is None:
                raise HTTPException(404, 'Model not found in this project.')
            task = run.get('task', 'duration')
            if task not in {'duration', 'phase'} or run.get('status') != 'completed':
                raise HTTPException(409, 'Candidate training is not completed; the approved active model remains available.')
            folder = registry.artifact_path(run['id'])
            if folder.is_symlink() or folder.resolve().parent != (registry.root/'experiments').resolve():
                raise HTTPException(409, 'Only locally generated experiment artifacts are permitted.')
            approval = self._approval(project_id, model_id)
            expected = approval or {}
        else:
            raise HTTPException(404, 'Model not found in the trusted registry.')
        manifest_name, artifact_name = _names(task)
        manifest_path, artifact_path = folder/manifest_name, folder/artifact_name
        if any(path.is_symlink() or not path.is_file() for path in (manifest_path, artifact_path)):
            raise HTTPException(409, 'Compatible saved model files are unavailable.')
        try:
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            manifest_sha, artifact_sha = _sha(manifest_path), _sha(artifact_path)
        except (OSError, ValueError):
            raise HTTPException(409, 'Saved model metadata is invalid.') from None
        if entry or approval:
            if expected.get('manifest_sha256') != manifest_sha or expected.get('artifact_sha256') != artifact_sha:
                raise HTTPException(409, 'Artifact or manifest checksum differs from its approved version. Approval is required again.')
        if manifest.get('artifact_sha256') and manifest['artifact_sha256'] != artifact_sha:
            raise HTTPException(409, 'Artifact checksum does not match its local manifest.')
        branch = _branch(manifest, task)
        gates = _gates(manifest, task, branch)
        if run:
            source = manifest.get('source_metadata', {})
            dataset = registry.get_dataset(run.get('dataset_id', ''))
            if (not dataset or dataset.get('is_fixture') or source.get('dataset_id') != dataset['id'] or
                source.get('sha256') != dataset['sha256'] or run.get('dataset_sha256') != dataset['sha256']):
                gates.append('Training dataset provenance does not match the registered local experiment.')
        source = manifest.get('source_metadata', {})
        metrics = manifest.get('models', {}).get(branch, {}).get('metrics', {})
        features = manifest.get('features', {})
        warnings = [RESEARCH_WARNING, manifest.get('warning', RETROSPECTIVE_WARNING)]
        if task == 'phase':
            warnings.append('Phase consistency classification is not trial success or progression probability.')
        public = {
            'id':model_id, 'name':entry.get('name', model_id) if entry else f'Project {task} model · {run["id"][:8]}',
            'task':task, 'branch':branch, 'status':'ineligible' if gates else 'approved' if approval else 'candidate',
            'active':False, 'artifact_version':manifest.get('artifact_version'), 'run_id':manifest.get('run_id'),
            'artifact_sha256':artifact_sha, 'manifest_sha256':manifest_sha,
            'training_dataset':_training_source(manifest),
            'validation_metrics':metrics.get('validation', {}), 'test_metrics':metrics.get('test', {}),
            'selection':manifest['duration_recommendation'] if task == 'duration' and (manifest.get('config', {}).get('enable_design_models') or 'duration_selection_metric' in manifest.get('config', {})) and branch != 'accuracy_task_selected' and manifest.get('duration_recommendation') else {'objective':'phase classification' if task == 'phase' else 'independent duration RMSE / risk Brier' if branch=='accuracy_task_selected' else 'duration MAE', 'data':'validation only',
                         'rule':'Recorded validation-selected phase classifier' if task == 'phase' else 'Independent minimum tuning RMSE and raw risk Brier; ties use model name' if branch=='accuracy_task_selected' else 'Minimum finite validation duration MAE; stable first candidate wins ties'},
            'features':features, 'approval_scope':'research_only', 'approval':approval,
            'gates':{'passed':not gates,'errors':gates}, 'warnings':warnings,
        }
        return {'id':model_id, 'task':task, 'branch':branch, 'directory':folder, 'manifest':manifest, 'model':public}

    def list_models(self, project_id, registry):
        identifiers = [(entry.get('id'), entry.get('task'), entry.get('name')) for entry in self._bundle_entries()]
        identifiers += [('project-'+run['id'], run.get('task','duration'), 'Project candidate '+run['id'][:8]) for run in registry.list_experiments()]
        items = []
        for model_id, task, name in identifiers:
            try:
                items.append(self._inspect(project_id, registry, model_id)['model'])
            except HTTPException as exc:
                items.append({'id':model_id, 'name':name, 'task':task, 'status':'unavailable','active':False,
                              'approval_scope':'research_only','warnings':[exc.detail], 'gates':{'passed':False,'errors':[exc.detail]}})
        active = {}
        configured = {}
        for task in ('duration','phase'):
            rows = self.store.execute('SELECT model_id FROM v5_active_models WHERE project_id=:project AND task=:task',{'project':project_id,'task':task},True)
            configured[task] = rows[0]['model_id'] if rows else None
            requested = configured[task] or next((m['id'] for m in items if m['task']==task and m['status']=='approved' and not m['id'].startswith('project-')), None)
            active[task] = next((m['id'] for m in items if m['id']==requested and m['status']=='approved'), None)
        for model in items:
            model['active'] = active.get(model['task']) == model['id']
            model['configured_active'] = configured.get(model['task']) == model['id']
        warnings = [f'The configured {task} model is unavailable. An owner must review its saved artifacts and approval.' for task in configured if configured[task] and not active[task]]
        if not identifiers:
            warnings.append('No trusted bundled release catalog is installed; inference remains unavailable until an owner approves a compatible local model.')
        return {'items':items, 'active':active, 'configured_active':configured, 'warnings':warnings}

    def resolve(self, project_id, registry, task='duration', model_id='active'):
        if task not in {'duration','phase'}:
            raise HTTPException(422, 'Unsupported model objective.')
        if model_id == 'active':
            rows = self.store.execute('SELECT model_id FROM v5_active_models WHERE project_id=:project AND task=:task',{'project':project_id,'task':task},True)
            model_id = rows[0]['model_id'] if rows else self.list_models(project_id, registry)['active'].get(task)
            if model_id is None:
                raise HTTPException(409, 'No approved saved model is active for this task. Owners may train and approve a research candidate separately.')
        result = self._inspect(project_id, registry, model_id)
        if result['task'] != task:
            raise HTTPException(422, 'Selected model does not match the requested objective.')
        if result['model']['status'] != 'approved':
            raise HTTPException(409, 'Research approval is required before this candidate can serve predictions.')
        return result

    def approve(self, project_id, registry, model_id, user_id, notes):
        result = self._inspect(project_id, registry, model_id)
        if not result['model']['gates']['passed']:
            raise HTTPException(422, {'message':'Model failed research approval gates.', 'errors':result['model']['gates']['errors']})
        if not model_id.startswith('project-'):
            return result['model']
        approval = {'scope':'research_only', 'approved_by':user_id,'approved_at':now(),'notes':notes,
                    'artifact_sha256':result['model']['artifact_sha256'],'manifest_sha256':result['model']['manifest_sha256'],
                    'gates':result['model']['gates']}
        self.store.execute('INSERT INTO v5_model_approvals(project_id,model_id,payload) VALUES (:project,:model,:payload) ON CONFLICT(project_id,model_id) DO UPDATE SET payload=excluded.payload',
                           {'project':project_id,'model':model_id,'payload':json.dumps(approval,allow_nan=False)})
        return self._inspect(project_id,registry,model_id)['model']

    def activate(self, project_id, registry, model_id):
        selected = self._inspect(project_id, registry, model_id)
        if selected['model']['status'] != 'approved':
            raise HTTPException(409, 'Approve the research candidate before activation.')
        self.store.execute('INSERT INTO v5_active_models(project_id,task,model_id,updated_at) VALUES (:project,:task,:model,:stamp) ON CONFLICT(project_id,task) DO UPDATE SET model_id=excluded.model_id,updated_at=excluded.updated_at',
                           {'project':project_id,'task':selected['task'],'model':model_id,'stamp':now()})
        return {**selected['model'], 'active':True}

    def initialize_project_defaults(self, project_id, registry):
        """Release defaults apply only at creation, preserving existing projects."""
        for entry in self._bundle_entries():
            if not entry.get('default_for_new_projects'):
                continue
            selected=self._inspect(project_id,registry,entry['id'])
            if selected['model']['status']!='approved':
                raise HTTPException(409,'The release research model failed verification. Existing project data is preserved.')
            self.store.execute('INSERT INTO v5_active_models(project_id,task,model_id,updated_at) VALUES (:project,:task,:model,:stamp) ON CONFLICT(project_id,task) DO NOTHING',
                {'project':project_id,'task':selected['task'],'model':selected['id'],'stamp':now()})

    def infer_rows(self, project_id, dataset_registry, rows, dataset, *, task='duration', model_id='active', mode='retrospective'):
        if dataset.get('is_fixture'):
            raise HTTPException(422, 'Software-test fixtures cannot support scientific inference.')
        if mode not in {'retrospective','pretrial'}:
            raise HTTPException(422, 'Choose retrospective or pretrial mode.')
        selected = self.resolve(project_id, dataset_registry, task=task, model_id=model_id)
        rows = list(rows)
        if not rows or len(rows)>1000:
            raise HTTPException(422, 'Provide between 1 and 1000 rows for saved inference.')
        manifest = selected['manifest']
        input_mode = _input_mode(manifest, selected['branch'])
        requirements = _input_requirements(manifest, selected['branch'])
        consumed = _consumed_features(requirements)
        # Missing individual values are imputed by the saved training pipeline;
        # absence of the entire modality is an incompatible input schema.
        for row in rows:
            if not _present(row.get('nct_id')) or not _present(row.get('title')):
                raise HTTPException(422, 'Inference schema requires nonempty nct_id and title.')
            for requirement in requirements:
                fields, component_mode = requirement['fields'], requirement['mode']
                structured = any(_present(row.get(name)) for name in fields['numeric'] + fields['categorical'])
                narrative = any(_present(row.get(name)) for name in fields['text'] if requirement['explicit'] or name != 'title')
                if (component_mode == 'structured' and not structured) or (component_mode == 'text' and not narrative) or (component_mode == 'multimodal' and not (structured or narrative)):
                    raise HTTPException(422, 'Input feature schema has no observed values for a selected model component. Supply its required protocol text or structured model features.')
        model = selected['model']
        result = {'id':uuid.uuid4().hex, 'created_at':now(),'mode':mode,'model':model,
                  'dataset':{key:dataset.get(key) for key in ('id','name','sha256','row_count')},
                  'items':[], 'warnings':[RESEARCH_WARNING, RETROSPECTIVE_WARNING if mode=='retrospective' else 'Pretrial availability checks use supplied timestamps; supplied provenance is not independent prospective validation.']}
        for raw in rows:
            row = json_clean(raw)
            warnings = self.availability_warnings(row, manifest, input_mode, mode, consumed=consumed)
            if mode == 'pretrial' and warnings:
                result['items'].append({'nct_id':row['nct_id'],'status':'blocked','prediction':None,'availability_warnings':warnings})
                continue
            try:
                if task == 'phase':
                    from src.clinical_trial_intelligence.phase_model import predict_phase
                    from .services.phase_service import normalize_phase_input
                    prediction = predict_phase(normalize_phase_input(row,manifest), selected['directory'])
                else:
                    from src.clinical_trial_intelligence.research import predict_trial
                    prediction = predict_trial(row, selected['directory'], model_name=selected['branch'])
                if prediction.get('status') != 'available':
                    prediction = {'status':'unavailable','reason':'The approved artifact could not produce a compatible finite prediction. Ask the owner to review its version and dependencies.'}
            except Exception:
                prediction = {'status':'unavailable','reason':'The approved artifact could not produce a compatible finite prediction.'}
            result['items'].append({'nct_id':row['nct_id'], 'status':prediction['status'], 'prediction':prediction, 'availability_warnings':warnings})
        result['summary'] = {'requested':len(rows), **{state:sum(item['status']==state for item in result['items']) for state in ('available','blocked','unavailable')}}
        return json_clean(result)

    @staticmethod
    def availability_warnings(row, manifest, input_mode, mode, *, consumed=None):
        features = manifest.get('features', {})
        if consumed is None:
            consumed = list(features.get('numeric', []))+list(features.get('categorical', [])) if input_mode in {'structured', 'multimodal'} else []
            if input_mode in {'text', 'multimodal'}:
                consumed += list(features.get('text', []))
        missing = [name for name in consumed if not _present(row.get(name))]
        if mode == 'retrospective':
            return [RETROSPECTIVE_WARNING] + (['Missing feature values use saved training imputers: '+', '.join(missing)+'.'] if missing else [])
        warnings = []
        cutoff = _availability_timestamp(row.get('prediction_as_of'))
        start = _availability_timestamp(row.get('start_date'), date_only=True)
        if pd.isna(cutoff):
            warnings.append('Missing valid prediction_as_of timestamp for the pretrial cutoff.')
        if pd.isna(start):
            warnings.append('An exact start_date is required to establish the pretrial cutoff.')
        elif pd.notna(cutoff) and cutoff > start:
            warnings.append('prediction_as_of is after trial start; this is not pretrial inference.')
        for field in consumed:
            if not _present(row.get(field)):
                continue
            stamp = _availability_timestamp(row.get(field+'_available_at'))
            if pd.isna(stamp):
                warnings.append(f'Missing valid {field}_available_at timestamp.')
            elif pd.notna(cutoff) and stamp > cutoff:
                warnings.append(f'{field} timestamp is later than prediction_as_of; blocked to prevent temporal leakage.')
        return warnings

    def save_batch(self, project_id, user_id, result):
        self.store.execute('INSERT INTO v5_inference_batches(id,project_id,dataset_id,user_id,created_at,payload) VALUES (:id,:project,:dataset,:user,:stamp,:payload)',
                           {'id':result['id'],'project':project_id,'dataset':result['dataset']['id'],'user':user_id,'stamp':result['created_at'],
                            'payload':json.dumps(result,allow_nan=False)})
        return result


class BatchInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: str = Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    model_id: str = Field(default='active',pattern=MODEL_ID_PATTERN)
    task: Literal['duration','phase'] = 'duration'
    limit: int = Field(default=100,ge=1,le=1000)
    mode: Literal['retrospective','pretrial'] = 'retrospective'


class ApproveInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    notes: str = Field(min_length=3,max_length=4000)
    research_only_acknowledged: Literal[True]


class ActivateInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    notes: str = Field(min_length=3,max_length=4000)


def attach_inference_routes(app):
    app.state.model_registry = ApprovedModelRegistry(app.state.platform_store)

    def context(request, owner=False):
        project = app.state.require_project(request,roles={'owner'} if owner else None)
        return project, app.state.project_registry(project['id']), app.state.model_registry

    @app.get('/api/v5/models')
    def models(request: Request):
        project, registry, service = context(request)
        return service.list_models(project['id'], registry)

    @app.post('/api/v5/models/{model_id}/approve')
    def approve(model_id: str, body: ApproveInput, request: Request):
        project, registry, service = context(request, True)
        user = app.state.current_user(request)
        result = service.approve(project['id'],registry,model_id,user['id'],body.notes)
        app.state.audit(project['id'],user['id'],'model.approve',{'model_id':model_id,'scope':'research_only','notes':body.notes})
        return result

    @app.post('/api/v5/models/{model_id}/activate')
    def activate(model_id: str, body: ActivateInput, request: Request):
        project, registry, service = context(request, True)
        result = service.activate(project['id'],registry,model_id)
        app.state.audit(project['id'],app.state.current_user(request)['id'],'model.activate',{'model_id':model_id,'notes':body.notes})
        return result

    @app.post('/api/v5/inference/batch',status_code=201)
    def infer(body: BatchInput, request: Request):
        app.state.require_project(request, roles={'owner','researcher','reviewer','viewer'})
        project, registry, service = context(request)
        dataset = registry.get_dataset(body.dataset_id)
        if dataset is None:
            raise HTTPException(404, 'Dataset not found in this project.')
        try:
            rows = registry.frame(body.dataset_id).head(body.limit).to_dict(orient='records')
        except (OSError, ValueError):
            raise HTTPException(422, 'Dataset canonical schema could not be read.') from None
        result = service.infer_rows(project['id'], registry, rows, dataset,task=body.task,model_id=body.model_id,mode=body.mode)
        user = app.state.current_user(request)
        service.save_batch(project['id'],user['id'],result)
        app.state.audit(project['id'],user['id'],'inference.batch',{'batch_id':result['id'],'dataset_id':body.dataset_id,'model_id':result['model']['id'],'mode':body.mode,'summary':result['summary']})
        return result

    @app.get('/api/v5/inference')
    def batches(request: Request, dataset_id: str | None = None):
        project, _, service = context(request)
        query = 'SELECT payload FROM v5_inference_batches WHERE project_id=:project'
        params = {'project':project['id']}
        if dataset_id:
            query += ' AND dataset_id=:dataset'
            params['dataset'] = dataset_id
        rows = service.store.execute(query+' ORDER BY created_at DESC LIMIT 100',params,True)
        return {'items':[json.loads(row['payload']) for row in rows]}

    @app.get('/api/v5/inference/{batch_id}')
    def batch_by_id(batch_id: str, request: Request):
        project, _, service = context(request)
        rows = service.store.execute('SELECT payload FROM v5_inference_batches WHERE id=:id AND project_id=:project',{'id':batch_id,'project':project['id']},True)
        if not rows:
            raise HTTPException(404, 'Inference batch not found in this project.')
        return json.loads(rows[0]['payload'])
