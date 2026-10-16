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
    branches, task_components = [], []
    def append_branch(name, task=None):
        component=MODEL_METADATA.get(name, {})
        component_mode=component.get('input_mode')
        if component_mode in {'structured','multimodal'}:
            encoder=('Training phase means shrunk toward global training statistics' if name=='accuracy_phase_shrinkage' else
                     'Training median imputation, log1p numeric transform, scaling and categorical encoding' if name=='accuracy_log_structured' else
                     'Fitted numeric imputation/scaling and categorical encoding')
            fields=['phase'] if name=='accuracy_phase_shrinkage' else [*NUMERIC_FEATURES,*CATEGORICAL_FEATURES]
            branch={'id':'structured','label':'Structured protocol metadata','encoder':encoder,'fields':fields}
            if not any(existing['id']==branch['id'] and existing['encoder']==encoder for existing in branches):branches.append(branch)
        if component_mode in {'text','multimodal'} and not any(existing['id']=='text' for existing in branches):
            branches.append({'id':'text','label':'Protocol narrative','encoder':'Training-fitted TF-IDF','fields':list(TEXT_FIELDS)})
        if task:task_components.append({'task':task,'model_name':name,'input_mode':component_mode})
    explanation = explain_prediction(prediction, row)
    components = explanation.get('components', [])
    architecture_method=explanation.get('method')
    reason=None if metadata else prediction.get('reason','No compatible saved model is available.')
    if mode=='composite':
        selected=[('duration',prediction.get('duration_explanation',{}).get('selected_component')),('risk',prediction.get('explanation',{}).get('selected_component'))]
        if all(name in MODEL_METADATA and MODEL_METADATA[name]['input_mode']!='composite' for _,name in selected):
            for task,name in selected:append_branch(name,task)
            architecture_method='Independent tuning-selected duration and risk branches'
        else:reason='Selected task component metadata is unavailable; architecture cannot be inferred.'
        components=[] # Independent task choices have no invented ensemble weights.
    else:append_branch(model)
    fusion = {'status':'available' if metadata and reason is None else 'unavailable','model_name':model,
              'input_mode':mode,'family':metadata.get('family'),'method':architecture_method,
              'branches':branches,'components':components,'task_components':task_components,'reason':reason}
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
