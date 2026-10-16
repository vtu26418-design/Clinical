import pytest
from fastapi import HTTPException
from backend.app.v5_inference import _branch, _input_mode


def test_task_selected_branch_is_opt_in_and_legacy_duration_selection_remains():
    manifest={'config':{},'models':{'median_baseline':{'metrics':{'validation':{'regression':{'mae':2}}}},'accuracy_task_selected':{'metrics':{'validation':{'regression':{'mae':3}}}}}}
    assert _branch(manifest,'duration')=='median_baseline'
    manifest['config']['enable_accuracy_models']=True
    assert _branch(manifest,'duration')=='accuracy_task_selected'


def test_composite_consumes_union_of_actual_selected_modalities():
    models={'choice':{'input_mode':'composite','selection':{'regressor_component':'a','classifier_component':'b'}},'a':{'input_mode':'structured'},'b':{'input_mode':'text'}}
    assert _input_mode({'models':models},'choice')=='multimodal'
    models['b']['input_mode']='baseline'
    assert _input_mode({'models':models},'choice')=='structured'
    models['a']['input_mode']='baseline'
    assert _input_mode({'models':models},'choice')=='baseline'
    models['choice']['selection']['classifier_component']='choice'
    with pytest.raises(HTTPException):_input_mode({'models':models},'choice')
