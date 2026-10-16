from backend.app.services.visualization_service import study_visualization


def packet(model,**extra):
    return study_visualization({'study':{'nct_id':'TEST','title':'Software architecture example'},'duration':{'status':'available','model_name':model,'duration_days':30,**extra},'provenance':{}})['fusion']


def test_selected_tasks_describe_real_architecture_without_fabricated_weights():
    value=packet('accuracy_task_selected',duration_explanation={'status':'unavailable','method':'local attribution unavailable','selected_component':'accuracy_log_structured'},explanation={'selected_component':'text'})
    assert value['input_mode']=='composite'
    assert {b['id'] for b in value['branches']}=={'structured','text'}
    assert 'log1p' in value['branches'][0]['encoder']
    assert 'TF-IDF' in value['branches'][1]['encoder']
    assert value['components']==[]
    assert 'Independent' in value['method']
    assert [c['model_name'] for c in value['task_components']]==['accuracy_log_structured','text']


def test_phase_shrinkage_consumes_training_phase_statistics_only():
    value=packet('accuracy_phase_shrinkage')
    assert value['branches'][0]['fields']==['phase']
    assert 'statistics' in value['branches'][0]['encoder']


def test_unknown_composite_metadata_stays_unavailable_instead_of_constant():
    value=packet('accuracy_task_selected')
    assert value['status']=='unavailable' and value['branches']==[]
    assert 'component' in value['reason']
