"""Predictions only from compatible artifacts produced by this server."""
import json

from .data_service import DatasetRegistry


def unavailable(reason='Train an eligible dataset to make model predictions available.') -> dict:
    return {'status': 'unavailable', 'probability': None, 'duration_days': None, 'model_name': None, 'explanation': None, 'reason': reason}


def compatible_artifacts(dataset: dict, registry: DatasetRegistry):
    """Yield only present, local artifacts with matching dataset provenance."""
    if dataset['is_fixture']:
        return
    from src.clinical_trial_intelligence.research import ARTIFACT_VERSION
    for experiment in registry.list_experiments(dataset['id']):
        if experiment.get('task', 'duration') != 'duration' or experiment['status'] != 'completed' or experiment.get('dataset_sha256') != dataset['sha256']:
            continue
        try:
            directory = registry.artifact_path(experiment['id'])
            # joblib executes Python when loaded. Never accept uploaded model
            # paths, provider URLs, or manifest-supplied path overrides.
            if directory.is_symlink() or directory.resolve().parent != (registry.root / 'experiments').resolve():
                continue
            manifest_file = directory / 'manifest.json'
            model_file = directory / 'models.joblib'
            if manifest_file.is_symlink() or model_file.is_symlink() or not model_file.is_file():
                continue
            manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
            if manifest.get('status') != 'completed' or manifest.get('artifact_version') != ARTIFACT_VERSION or not manifest.get('run_id'):
                continue
            metadata = manifest.get('source_metadata') or manifest.get('dataset') or {}
            if metadata.get('dataset_id') != dataset['id'] or metadata.get('sha256') != dataset['sha256']:
                continue
            yield directory
        except (OSError, ValueError, KeyError, AttributeError, TypeError):
            continue


def predict(row: dict, dataset: dict, registry: DatasetRegistry, model_name='recommended') -> dict:
    if dataset['is_fixture']:
        return unavailable('Bundled fixtures are software test data and do not support scientific predictions.')
    # The v5 platform supplies a project-scoped approval resolver. A new upload
    # uses the saved approved model immediately; it never triggers training.
    resolver = getattr(registry, 'approved_model_resolver', None)
    if resolver is not None:
        try:
            from src.clinical_trial_intelligence.research import predict_trial
            approved = resolver(task='duration', model_name=model_name)
            selected = approved['branch'] if model_name == 'recommended' else model_name
            if selected not in approved['manifest']['models']:
                return unavailable('The requested branch is absent from the approved saved model.')
            result = predict_trial(row, approved['directory'], model_name=selected)
            if result.get('status') == 'available':
                return {**result, 'approved_model_id': approved['id'],
                        'artifact_sha256': approved['model']['artifact_sha256'],
                        'approval_scope': 'research_only'}
        except Exception:
            pass
        return unavailable('No compatible approved saved research model is available. An owner must review the model registry.')
    attempted = False
    for directory in compatible_artifacts(dataset, registry):
        attempted = True
        try:
            from src.clinical_trial_intelligence.research import predict_trial
            selected = model_name
            if selected == 'recommended':
                selected = json.loads((directory / 'manifest.json').read_text(encoding='utf-8')).get('recommended_model', 'multimodal')
            result = predict_trial(row, directory, model_name=selected)
            if result.get('status') == 'available':
                return result
        except Exception:
            # A damaged local artifact must not turn a descriptive study view
            # into an error page or expose server paths/provider information.
            continue
    if attempted:
        return unavailable('The trained artifacts are unavailable or incompatible; rerun an experiment.')
    return unavailable()
