"""Read-only, project-resolved model quality from actual saved prediction rows.

No estimator is deserialized. The platform gateway supplies membership/role
checks; the research application's normal token dependency is retained here.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from .config import PROJECT_ROOT


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _local_file(directory: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or Path(name).name != name or '\\' in name:
        raise ValueError('Evidence names must be local basenames')
    path = directory / name
    if path.is_symlink() or not path.is_file() or path.resolve().parent != directory.resolve():
        raise ValueError('Evidence file is unavailable or outside the trusted model')
    return path


def _resolve(registry, task: str, model_id: str) -> dict:
    resolver = getattr(registry, 'approved_model_resolver', None)
    if callable(resolver):
        return resolver(task=task, model_id=model_id)
    # Standalone research mode has no platform project registry. Only exact
    # release catalog entries are allowed; query input can never supply a path.
    from .v5_inference import _branch, _gates
    catalog = json.loads((PROJECT_ROOT / 'examples/approved-models-v5.json').read_text(encoding='utf-8'))
    entry = next((item for item in catalog['models'] if item.get('task') == task and (model_id == 'active' or item.get('id') == model_id)), None)
    if not entry:
        raise HTTPException(404, 'Approved model not found.')
    if entry.get('approval', {}).get('scope') != 'research_only':
        raise ValueError('Missing research release approval')
    relative = Path(entry['directory'])
    directory = PROJECT_ROOT / relative
    if relative.is_absolute() or directory.is_symlink() or directory.resolve().parent != (PROJECT_ROOT / 'examples').resolve():
        raise ValueError('Invalid trusted release directory')
    manifest_name = 'phase_manifest.json' if task == 'phase' else 'manifest.json'
    manifest = json.loads(_local_file(directory, manifest_name).read_text(encoding='utf-8'))
    branch = _branch(manifest, task)
    if _gates(manifest, task, branch):
        raise ValueError('Trusted release does not pass research model eligibility gates')
    public = {key: entry.get(key) for key in ('id', 'name', 'task', 'manifest_sha256', 'artifact_sha256', 'approval')}
    public.update(branch=branch, status='approved', artifact_version=manifest.get('artifact_version'), run_id=manifest.get('run_id'), approval_scope='research_only')
    return {'directory': directory, 'branch': branch, 'model': public, 'task': task}


def _quality(registry, task: str, model_id: str, split: str) -> dict:
    from src.clinical_trial_intelligence.model_analysis import analyze_experiment, _read_json
    selected = _resolve(registry, task, model_id)
    directory, public = Path(selected['directory']), selected['model']
    if directory.is_symlink() or selected.get('task') != task or public.get('status') != 'approved':
        raise ValueError('An approved compatible model is required')
    manifest_path = _local_file(directory, 'phase_manifest.json' if task == 'phase' else 'manifest.json')
    artifact_path = _local_file(directory, 'phase_models.joblib' if task == 'phase' else 'models.joblib')
    checked = {manifest_path.name: _sha(manifest_path), artifact_path.name: _sha(artifact_path)}
    for path, key in ((manifest_path, 'manifest_sha256'), (artifact_path, 'artifact_sha256')):
        expected = public.get(key)
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected) or checked[path.name] != expected:
            raise ValueError('Approved artifact or manifest checksum differs')
    manifest = _read_json(manifest_path)
    if manifest.get('task', 'duration') != task:
        raise ValueError('Saved evidence task does not match the requested task')
    definition = manifest.get('splits', {}).get(split)
    if not isinstance(definition, dict):
        raise HTTPException(422, 'Selected split is not declared for this model.')
    if definition.get('role', split) == 'train' or split == 'train':
        raise HTTPException(422, 'Training predictions cannot establish held-out model quality.')
    branch = selected['branch']
    models = manifest.get('models', {})
    if branch not in models:
        raise ValueError('Selected branch is absent from saved evidence')
    baseline_name = next((name for name, meta in models.items() if name in {'median_baseline', 'majority_baseline'} or meta.get('input_mode') == 'baseline'), None)
    names = {branch} | ({baseline_name} if baseline_name else set())
    prefix = 'phase_' if task == 'phase' else ''
    evidence_paths = [_local_file(directory, manifest.get('files', {}).get(key, prefix + fallback)) for key, fallback in [('predictions', 'held_out_predictions.csv'), ('metrics', 'metrics.json')]]
    evidence_hashes = {path.name: _sha(path) for path in evidence_paths}
    recorded_hashes = manifest.get('evaluation_hashes', {})
    if not isinstance(recorded_hashes, dict):
        raise ValueError('Invalid evaluation checksum metadata')
    for name, digest in evidence_hashes.items():
        if name in recorded_hashes and recorded_hashes[name] != digest:
            raise ValueError('Evaluation evidence checksum differs from approved manifest')
    report = analyze_experiment(directory, model_names=names, split=split, chart_point_limit=600)
    # Recheck after reading. Do not serve rows from an artifact changed while a
    # report was being recomputed, even if a resolver had inspected it earlier.
    for path in [manifest_path, artifact_path, *evidence_paths]:
        expected = checked.get(path.name, evidence_hashes.get(path.name))
        if path.is_symlink() or _sha(path) != expected:
            raise ValueError('Evidence changed during inspection')
    if any(report['hashes'].get(name) != digest for name, digest in {**evidence_hashes, manifest_path.name: checked[manifest_path.name]}.items()):
        raise ValueError('Analyzed evidence differs from inspected evidence')
    chosen = next((row for row in report['models'] if row['model_name'] == branch), None)
    if not chosen:
        raise ValueError('Selected branch has no held-out evaluation')
    baseline = next((row for row in report['models'] if row['model_name'] == baseline_name), None)
    report['charts'] = [chart for chart in report['charts'] if chart['model_name'] == branch]
    source = manifest.get('source_metadata', {})
    report['provenance'].update({key: source[key] for key in ('endpoint', 'source_sha256', 'sha256', 'dataset_id', 'acquisition_started_at') if key in source})
    safe_public = {key: public.get(key) for key in ('id', 'name', 'task', 'branch', 'status', 'artifact_version', 'run_id', 'manifest_sha256', 'artifact_sha256', 'approval_scope', 'selection')}
    safe_public['branch'] = branch
    endpoint = ({'duration_unit': 'days', 'prolonged_threshold_days': manifest.get('target', {}).get('prolonged_threshold_days'),
                 'meaning': 'Observed completed-trial duration and probability of exceeding the training-only duration threshold; not trial success, adverse-event risk, or phase progression.',
                 'probability_semantics': 'Raw prolonged probabilities; separately labeled calibrated probabilities only when saved.'} if task == 'duration' else
                {'labels': manifest.get('labels', []), 'meaning': 'Consistency with the recorded registry phase label; not trial success or probability of progressing to a later phase.',
                 'probability_semantics': 'Class scores; calibration is assessed separately using one-vs-rest reliability.'})
    declared_interval = models[branch].get('uncertainty', {})
    interval = {key: declared_interval[key] for key in ('status', 'method', 'split', 'n', 'alpha', 'nominal_coverage', 'rank', 'residual_quantile_days', 'bounded', 'interpretation') if key in declared_interval}
    uncertainty = {'metric_confidence_intervals': {'status': 'unavailable', 'reason': 'No independently recomputed sampling confidence interval is supplied. Point estimates and exact class support are shown; temporal shift and small samples limit inference.'},
                   'prediction_intervals': {'status': 'unavailable', **interval, 'evidence': 'Recorded approved manifest metadata; prediction intervals are distinct from confidence intervals for accuracy metrics.'}}
    declared_ci = models[branch].get('metrics', {}).get(split, {}).get('confidence_intervals', {})
    if isinstance(declared_ci, dict) and declared_ci.get('requested_resamples', 0):
        recorded = {key: declared_ci[key] for key in ('method', 'level', 'requested_resamples', 'random_seed', 'interpretation') if key in declared_ci}
        for metric in ('mae', 'rmse', 'median_absolute_error', 'r2', 'auroc', 'average_precision', 'brier', 'log_loss', 'accuracy', 'balanced_accuracy', 'macro_f1'):
            value = declared_ci.get(metric)
            if not isinstance(value, dict):
                continue
            lower, upper, count = (value.get(key) for key in ('lower', 'upper', 'valid_resamples'))
            if type(count) is not int or count < 0 or count > declared_ci['requested_resamples']:
                raise ValueError('Invalid recorded confidence interval support')
            if (lower is None) != (upper is None) or any(type(bound) not in (int, float) or not math.isfinite(bound) for bound in (lower, upper) if bound is not None) or (lower is not None and lower > upper):
                raise ValueError('Invalid recorded confidence interval bounds')
            recorded[metric] = {'lower': lower, 'upper': upper, 'valid_resamples': count}
        uncertainty['metric_confidence_intervals'] = {
            'status': 'recorded_not_recomputed', 'model_name': branch, 'split': split,
            'source': 'approved manifest model/split metrics', 'recorded': recorded,
            'reason': 'These bootstrap confidence intervals are recorded in the approved manifest and are not independently recomputed by this check. Point metrics are recomputed from all saved prediction rows. Trial bootstrap intervals condition on the fitted model and assume independent trials; they do not account for retraining, clustering or temporal shift.'}
    integrity = {'artifact_and_manifest': 'verified_against_approval', 'evaluation_files': 'hashed_and_split_membership_validated',
                 'evaluation_bound_to_approval': all(path.name in recorded_hashes for path in evidence_paths),
                 'estimator_deserialized': False, 'hashes': {**checked, **evidence_hashes}}
    warnings = list(dict.fromkeys([*public.get('warnings', []), *report['limitations']]))
    if not integrity['evaluation_bound_to_approval']:
        warnings.append('This older manifest does not bind all evaluation-file checksums to its approval. Their current hashes and complete split memberships are checked; the approval binds the estimator and manifest.')
    report.update(schema_version=1, model=safe_public, selected_split=split, selected=chosen, baseline=baseline,
                  endpoint=endpoint, integrity=integrity, uncertainty=uncertainty, warnings=warnings)
    report['quality_context'] = {key: report[key] for key in ('model', 'selected_split', 'endpoint', 'integrity', 'uncertainty', 'warnings')}
    # All public evidence must be finite JSON; nothing from the request is used
    # to resolve a filesystem path or to deserialize an estimator.
    json.dumps(report, allow_nan=False)
    return report


def attach_model_quality(app, registry, require_token):
    router = APIRouter(dependencies=[Depends(require_token)])

    @router.get('/api/v1/model-quality')
    def model_quality(task: Literal['duration', 'phase'] = 'duration',
                      model_id: str = Query(default='active', pattern=r'^[a-zA-Z0-9_-]{1,100}$'),
                      split: str = Query(default='test', pattern=r'^[a-zA-Z0-9_-]{1,50}$'),
                      format: Literal['json', 'html', 'csv'] = 'json'):
        from src.clinical_trial_intelligence.model_analysis import render_analysis_csv, render_analysis_html
        try:
            report = _quality(registry, task, model_id, split)
        except (ValueError, OSError, KeyError, TypeError, StopIteration):
            raise HTTPException(409, 'Saved model quality evidence is incomplete, invalid, or differs from its approved version. An owner must review the model evidence.') from None
        headers = {'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'}
        if format == 'json':
            return Response(json.dumps(report, allow_nan=False), media_type='application/json', headers=headers)
        headers['Content-Disposition'] = f'attachment; filename="{task}-model-quality.{format}"'
        if format == 'html':
            headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; base-uri 'none'; form-action 'none'"
            return HTMLResponse(render_analysis_html(report), headers=headers)
        return Response(render_analysis_csv(report), media_type='text/csv', headers=headers)

    app.include_router(router)
