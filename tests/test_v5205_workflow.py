"""Software-only workflow regressions; no clinical-performance claims."""
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi import HTTPException
from backend.app.v5_inference import ApprovedModelRegistry
from backend.app.services.training_preflight import preflight
from src.clinical_trial_intelligence.research import ExperimentConfig


def service(monkeypatch, models, branch):
    manifest={'features':{'numeric':['enrollment'],'categorical':['phase'],'text':['title','brief_summary']},'models':models}
    value=ApprovedModelRegistry.__new__(ApprovedModelRegistry)
    value.resolve=lambda *args,**kwargs:{'manifest':manifest,'branch':branch,'model':{'id':'saved','task':'duration'},'directory':Path('/unused')}
    monkeypatch.setattr('src.clinical_trial_intelligence.research.predict_trial',lambda *args,**kwargs:{'status':'available','duration_days':20,'probability':.2})
    return value


def infer(value, row, mode='retrospective'):
    return value.infer_rows('project',None,[{'nct_id':'SOFTWARE1','title':'Software-only fixture',**row}],{'id':'software','is_fixture':False},mode=mode)


def test_constant_branch_requires_no_observed_model_features(monkeypatch):
    value=service(monkeypatch,{'median_baseline':{'input_mode':'baseline'}},'median_baseline')
    assert infer(value,{})['summary']['available']==1


def test_phase_shrinkage_accepts_only_its_phase_input(monkeypatch):
    value=service(monkeypatch,{'accuracy_phase_shrinkage':{'input_mode':'structured'}},'accuracy_phase_shrinkage')
    result=infer(value,{'phase':'PHASE2','prediction_as_of':'2020-01-01','start_date':'2020-01-01','phase_available_at':'2019-12-31'},'pretrial')
    assert result['summary']['available']==1


def test_composite_requires_each_component_and_checks_only_union(monkeypatch):
    models={'choice':{'input_mode':'composite','selection':{'regressor_component':'phase','classifier_component':'narrative'}},
            'phase':{'input_mode':'structured','input_features':{'categorical':['phase']}},
            'narrative':{'input_mode':'text','input_features':{'text':['brief_summary']}}}
    value=service(monkeypatch,models,'choice')
    with pytest.raises(HTTPException,match='') as error:infer(value,{'brief_summary':'Observed software text'})
    assert error.value.status_code==422
    row={'phase':'PHASE2','brief_summary':'Observed software text','prediction_as_of':'2020-01-01','start_date':'2020-01-01',
         'phase_available_at':'2019-12-31','brief_summary_available_at':'2019-12-31','enrollment':100}
    assert infer(value,row,'pretrial')['summary']['available']==1


def test_exact_branch_input_features_override_global_modalities(monkeypatch):
    models={'new':{'input_mode':'structured','input_features':{'numeric':['planned_enrollment'],'categorical':['allocation'],'text':[]}}}
    value=service(monkeypatch,models,'new')
    with pytest.raises(HTTPException):infer(value,{'enrollment':100})
    assert infer(value,{'allocation':'RANDOMIZED'})['summary']['available']==1
    row={'planned_enrollment':100,'planned_enrollment_available_at':'2019-12-31','prediction_as_of':'2020-01-01','start_date':'2020-01-01','enrollment':200}
    assert infer(value,row,'pretrial')['summary']['available']==1


def test_unavailable_configured_model_is_not_usable_active(monkeypatch):
    value=ApprovedModelRegistry.__new__(ApprovedModelRegistry)
    value._bundle_entries=lambda:[{'id':'broken','task':'duration','name':'Broken'}]
    value._inspect=lambda *args:(_ for _ in ()).throw(HTTPException(409,'Artifact checksum mismatch.'))
    value.store=type('Store',(),{'execute':lambda self,sql,params,fetch:[{'model_id':'broken'}] if params['task']=='duration' else []})()
    result=value.list_models('project',type('Registry',(),{'list_experiments':lambda self:[]})())
    assert result['items'][0]['active'] is False
    assert result['items'][0]['configured_active'] is True
    assert result['active']['duration'] is None


def test_default_listing_and_resolver_choose_same_usable_bundle():
    value=ApprovedModelRegistry.__new__(ApprovedModelRegistry)
    value.store=type('Store',(),{'execute':lambda *args:[]})()
    value._bundle_entries=lambda:[{'id':'broken','task':'duration'},{'id':'good','task':'duration'}]
    def inspect(project,registry,identifier):
        if identifier=='broken':raise HTTPException(409,'Missing artifact.')
        return {'id':identifier,'task':'duration','model':{'id':identifier,'task':'duration','status':'approved'}}
    value._inspect=inspect
    registry=type('Registry',(),{'list_experiments':lambda self:[]})()
    assert value.list_models('p',registry)['active']['duration']==value.resolve('p',registry)['id']=='good'


def test_preflight_reports_effective_partition_and_requested_configuration():
    frame=pd.read_csv(Path(__file__).resolve().parents[1]/'data/starter/trials.csv')
    config=ExperimentConfig(train_fraction=.55,validation_fraction=.25,enable_accuracy_models=True)
    result=preflight(frame,{'fixture':False},'duration',20000,config=config)
    from src.clinical_trial_intelligence.research import prepare_cohort,temporal_split,partition_validation
    cohort,_=prepare_cohort(frame)
    splits=temporal_split(cohort,config)
    tuning,calibration,_=partition_validation(splits['validation'])
    assert result['ready'] is True
    assert result['splits']['validation']==len(tuning)
    assert result['splits']['calibration']==len(calibration)
    assert result['effective_config']['enable_accuracy_models'] is True
    assert result['effective_config']['train_fraction']==.55


@pytest.mark.parametrize('task', ['duration', 'phase'])
def test_training_and_readiness_forward_design_configuration(tmp_path, monkeypatch, task):
    from fastapi.testclient import TestClient
    from backend.app.main import create_research_app
    from backend.app.config import Settings
    module = 'src.clinical_trial_intelligence.' + ('research' if task == 'duration' else 'phase_model')
    captured = []
    def train(df, output, source_metadata, *, config):
        captured.append(config)
        return {'status':'completed'}
    monkeypatch.setattr(module + ('.train_experiment' if task == 'duration' else '.train_phase_experiment'), train)
    options = {'enable_design_models':True, 'enable_design_catboost':False, 'duration_selection_metric':'mae'}
    with TestClient(create_research_app(Settings(storage_dir=str(tmp_path), _env_file=None))) as client:
        source = client.post('/api/v1/datasets/starter').json()
        readiness = client.get('/api/v1/readiness', params={'dataset_id':source['id'], **options})
        assert readiness.status_code == 200
        check = readiness.json()[task]
        assert check['ready'] is True
        assert check['effective_config']['enable_design_models'] is True
        assert check['effective_config']['enable_design_catboost'] is False
        if task == 'duration':
            assert check['effective_config']['duration_selection_metric'] == 'mae'
        endpoint = '/api/v1/' + ('experiments' if task == 'duration' else 'phase-experiments')
        response = client.post(endpoint, json={'dataset_id':source['id'], **options})
        assert response.status_code == 202, response.text
        for name, value in options.items():
            assert response.json()[name] == value
        assert len(captured) == 1
        assert captured[0].enable_design_models is True
        assert captured[0].enable_design_catboost is False
        if task == 'duration':
            assert captured[0].duration_selection_metric == 'mae'
        assert client.post(endpoint, json={'dataset_id':source['id'], 'enable_design_catboost':True}).status_code == 422
        assert client.post(endpoint, json={'dataset_id':source['id'], 'duration_selection_metric':'test-r2'}).status_code == 422


def test_design_branch_uses_recorded_duration_champion_without_changing_legacy():
    from backend.app.v5_inference import _branch
    manifest = {'config':{}, 'recommended_duration_model':'new', 'models':{
        'legacy':{'metrics':{'validation':{'regression':{'mae':1}}}},
        'new':{'metrics':{'validation':{'regression':{'mae':10}}}}}}
    assert _branch(manifest, 'duration') == 'legacy'
    manifest['config']['enable_design_models'] = True
    assert _branch(manifest, 'duration') == 'new'
    manifest['recommended_duration_model'] = None
    assert _branch(manifest, 'duration') is None


def test_design_mae_serves_independently_selected_risk_not_tie_winning_regressor():
    from backend.app.v5_inference import _branch
    manifest={'config':{'enable_design_models':True,'duration_selection_metric':'mae'},
              'recommended_duration_model':'regression_component','models':{'regression_component':{},'design_task_selected':{}}}
    assert _branch(manifest,'duration')=='design_task_selected'
    manifest['config']['duration_selection_metric']='rmse'
    assert _branch(manifest,'duration')=='regression_component'


def test_preflight_detects_missing_design_catboost_before_queue(monkeypatch):
    monkeypatch.setattr('backend.app.services.training_preflight.find_spec', lambda name: None)
    result = preflight(pd.DataFrame(), {'fixture':False}, 'duration', 100,
                       config=ExperimentConfig(enable_design_models=True, enable_design_catboost=True))
    assert result['ready'] is False
    assert 'Design CatBoost' in result['reason']


def test_exact_input_contract_overrides_mode_heuristics_and_supports_empty_constant(monkeypatch):
    models = {'contract':{'input_mode':'structured', 'input_features':{'numeric':[], 'categorical':[], 'text':['brief_summary']}}}
    value = service(monkeypatch, models, 'contract')
    assert infer(value, {'brief_summary':'Observed software-only source text'})['summary']['available'] == 1
    with pytest.raises(HTTPException):
        infer(value, {'phase':'PHASE2'})
    models['contract']['input_features']['text'] = []
    assert infer(value, {})['summary']['available'] == 1


def test_new_manifest_objective_uses_recorded_champion_and_old_bundles_replay():
    from backend.app.v5_inference import _branch
    root = Path(__file__).resolve().parents[1]
    old = json.loads((root/'examples/starter-duration-v5/manifest.json').read_text())
    assert 'duration_selection_metric' not in old['config']
    assert _branch(old, 'duration') == 'median_baseline'
    new = {**old, 'config':{**old['config'], 'duration_selection_metric':'rmse'}, 'recommended_duration_model':'structured'}
    assert _branch(new, 'duration') == 'structured'
    new['config']['enable_accuracy_models'] = True
    new['models']['accuracy_task_selected'] = {}
    assert _branch(new, 'duration') == 'accuracy_task_selected'


def test_nested_composite_uses_only_selected_task_contracts(monkeypatch):
    empty = {'numeric':[], 'categorical':[], 'text':[]}
    phase = {'numeric':[], 'categorical':['phase'], 'text':[]}
    models = {
        'choice':{'input_mode':'composite', 'selection':{'regressor_component':'constant', 'classifier_component':'nested'},
                  'task_input_features':{'regressor':empty, 'classifier':phase}},
        'constant':{'input_mode':'baseline'},
        'nested':{'input_mode':'composite', 'selection':{'regressor_component':'narrative', 'classifier_component':'phase'}},
        'narrative':{'input_mode':'text', 'input_features':{'text':['brief_summary']}},
        'phase':{'input_mode':'structured', 'input_features':phase}}
    value = service(monkeypatch, models, 'choice')
    row = {'phase':'PHASE2', 'prediction_as_of':'2020-01-01', 'start_date':'2020-01-01', 'phase_available_at':'2019-12-31'}
    assert infer(value, row, 'pretrial')['summary']['available'] == 1
    with pytest.raises(HTTPException):
        infer(value, {'brief_summary':'An unconsumed software-only narrative'})
