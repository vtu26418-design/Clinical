"""Study animation packets bound to the actual source and fitted model outputs."""
from datetime import date, timedelta

import pandas as pd

from .cohort_graphs import date_info, observed_duration, recruitment_summary, present
from .shap_adapter import explain_prediction


def study_visualization(workspace):
    row = workspace['study']
    prediction = workspace['duration']
    dates = []
    for field, label in [('start_date', 'Start'), ('primary_completion_date', 'Primary completion'), ('completion_date', 'Completion')]:
        value, precision = date_info(row.get(field))
        dates.append({'field': field, 'label': label, 'value': value, 'precision': precision,
                      'date_type': row.get(field + '_type') if present(row.get(field + '_type')) else None,
                      'availability': 'available' if value else 'unavailable'})
    observed = observed_duration(row)
    estimated_duration = prediction.get('duration_days') if prediction.get('status') == 'available' else None
    predicted_completion = None
    if dates[0]['precision'] == 'day' and estimated_duration is not None:
        try:
            predicted_completion = (date.fromisoformat(dates[0]['value']) + timedelta(days=estimated_duration)).isoformat()
        except (OverflowError, ValueError):
            pass
    timeline = {'status': 'available' if all(item['value'] is not None for item in dates) else
                         'partial' if any(item['value'] is not None for item in dates) else 'unavailable',
                'dates': dates, 'observed_duration_days': observed, 'predicted_duration_days': estimated_duration,
                'predicted_completion_date': predicted_completion, 'stage_durations': None,
                'reason': 'Reported dates preserve source precision. Predicted overall completion uses the saved duration model only; stage durations are not modelled.'}
    from src.clinical_trial_intelligence.research import MODEL_METADATA, NUMERIC_FEATURES, CATEGORICAL_FEATURES, TEXT_FIELDS
    model = prediction.get('model_name')
    metadata = MODEL_METADATA.get(model, {}) if prediction.get('status') == 'available' else {}
    mode = metadata.get('input_mode')
    branches = []
    if mode in {'structured', 'multimodal'}:
        branches.append({'id': 'structured', 'label': 'Structured protocol metadata',
                         'encoder': 'Fitted numeric imputation/scaling and categorical encoding',
                         'fields': [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]})
    if mode in {'text', 'multimodal'}:
        branches.append({'id': 'text', 'label': 'Protocol narrative', 'encoder': 'Training-fitted TF-IDF', 'fields': list(TEXT_FIELDS)})
    explanation = explain_prediction(prediction, row)
    components = explanation.get('components', [])
    fusion = {'status': 'available' if metadata else 'unavailable', 'model_name': model,
              'input_mode': mode, 'family': metadata.get('family'), 'method': explanation.get('method'),
              'branches': branches, 'components': components,
              'reason': None if metadata else prediction.get('reason', 'No compatible saved model is available.')}
    return {'workspace': workspace, 'timeline': timeline,
            'recruitment': recruitment_summary(pd.DataFrame([row])), 'fusion': fusion,
            'explanation': explanation, 'provenance': {**workspace['provenance'],
                'model_name': prediction.get('model_name'), 'run_id': prediction.get('run_id'),
                'artifact_sha256': prediction.get('artifact_sha256'), 'manifest_sha256': prediction.get('manifest_sha256'),
                'pipeline_source_sha256': prediction.get('pipeline_source_sha256')}}


def pipeline_status(experiments):
    experiments = sorted(experiments, key=lambda item: item.get('created_at', ''), reverse=True)
    active = [item for item in experiments if item.get('status') in {'queued', 'running'}]
    latest = active[0] if active else experiments[0] if experiments else None
    state = latest.get('status', 'unknown') if latest else 'idle'
    step = {'idle': 'Standby', 'queued': 'Queued', 'running': 'Training experiment',
            'completed': 'Experiment completed', 'failed': 'Experiment failed'}.get(state, 'Unknown experiment state')
    queue = 'active' if state == 'queued' else 'complete' if state in {'running', 'completed', 'failed'} else 'unknown'
    training = 'active' if state == 'running' else 'complete' if state == 'completed' else 'failed' if state == 'failed' else 'pending' if state == 'queued' else 'unknown'
    artifacts = 'complete' if state == 'completed' else 'failed' if state == 'failed' else 'pending' if state in {'queued', 'running'} else 'unknown'
    return {'status': state, 'current_task': latest.get('task') if latest else None,
            'current_step': step, 'overall_progress': None, 'experiment': latest,
            'pipeline_steps': [{'name': 'Queue', 'status': queue}, {'name': 'Training', 'status': training},
                               {'name': 'Saved artifacts', 'status': artifacts}],
            'active_experiments_count': len(active), 'total_experiments_count': len(experiments),
            'progress_available': False}
