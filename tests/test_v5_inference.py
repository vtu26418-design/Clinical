"""Saved inference acceptance using authentic frozen artifacts, never generated evidence."""
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app.config import PROJECT_ROOT, Settings
from backend.app.main import create_app


def config(tmp_path):
    return Settings(storage_dir=str(tmp_path), database_url='', auth_mode='local', _env_file=None)


def forbid_fit(*args, **kwargs):
    raise AssertionError('Inference must never train or fit preprocessing')


def test_models_endpoint_exists_without_startup_fitting(tmp_path, monkeypatch):
    from sklearn.pipeline import Pipeline
    monkeypatch.setattr(Pipeline, 'fit', forbid_fit)
    with TestClient(create_app(config(tmp_path))) as client:
        result = client.get('/api/v5/models')
        assert result.status_code == 200, result.text
        assert 'items' in result.json()


@pytest.fixture
def client(tmp_path):
    from backend.app.v5_inference import ApprovedModelRegistry
    entries = []
    for task, mf, af in [('duration', 'manifest.json', 'models.joblib'), ('phase', 'phase_manifest.json', 'phase_models.joblib')]:
        folder = PROJECT_ROOT / f'examples/starter-{task}-v4'
        entries.append({'id':f'bundled-{task}-test', 'name':f'Authentic {task} acceptance artifact', 'task':task,
            'directory':str(folder.relative_to(PROJECT_ROOT)),
            'manifest_sha256':hashlib.sha256((folder/mf).read_bytes()).hexdigest(),
            'artifact_sha256':hashlib.sha256((folder/af).read_bytes()).hexdigest(),
            'approval':{'scope':'research_only','approved_by':'acceptance test release','approved_at':'2026-10-09T00:00:00Z','notes':'Existing authentic retrospective artifact; test harness only.'}})
    catalog = tmp_path/'test-release.json'
    catalog.write_text(json.dumps({'release':'acceptance','models':entries}))
    app = create_app(config(tmp_path))
    app.state.model_registry = ApprovedModelRegistry(app.state.platform_store, catalog_path=catalog)
    with TestClient(app) as api:
        frame = pd.read_csv(PROJECT_ROOT/'data/starter/trials.csv').head(2)
        frame['nct_id'] = ['NEW-INFERENCE-001','NEW-INFERENCE-002']
        dataset = app.state.project_registry('local').register_bytes(frame.to_csv(index=False).encode(), 'new.csv')
        api.dataset = dataset
        api.catalog = catalog
        yield api


def batch(client, **kwargs):
    return client.post('/api/v5/inference/batch', json={'dataset_id':client.dataset['id'], 'limit':2, **kwargs})


def candidate(client, identifier='a'*32, task='duration', project_id='local'):
    registry = client.app.state.project_registry(project_id)
    manifest_file = 'manifest.json' if task == 'duration' else 'phase_manifest.json'
    folder = PROJECT_ROOT/f'examples/starter-{task}-v4'
    manifest = json.loads((folder/manifest_file).read_text())
    source = manifest['source_metadata']
    if registry.get_dataset(source['dataset_id']) is None:
        registry.register_bytes((PROJECT_ROOT/'data/starter/trials.csv').read_bytes(), 'starter.csv', dataset_id=source['dataset_id'])
    output = registry.artifact_path(identifier)
    shutil.copytree(folder, output)
    registry.save_experiment({'id':identifier,'task':task,'status':'completed','dataset_id':source['dataset_id'],
        'dataset_sha256':source['sha256'],'created_at':'2026-10-09T00:00:00Z','manifest':manifest})
    return 'project-'+identifier


def test_new_upload_predicts_without_training_and_has_provenance(client, monkeypatch):
    from sklearn.pipeline import Pipeline
    monkeypatch.setattr(Pipeline,'fit',forbid_fit)
    response = batch(client)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data['summary']['available'] == 2
    assert data['dataset']['sha256'] == client.dataset['sha256']
    assert data['model']['artifact_sha256']
    assert data['model']['artifact_version'] == 3
    prediction = data['items'][0]['prediction']
    assert prediction['duration_days'] > 0
    assert 0 <= prediction['probability'] <= 1
    assert prediction['explanation']['method']
    assert prediction['cohort_membership'] == 'not_in_retained_splits'
    assert data['items'][0]['availability_warnings']
    assert client.app.state.project_registry('local').list_experiments() == []


def test_saved_batch_and_model_activation_survive_restart(client):
    original = batch(client).json()
    app = create_app(client.app.state.settings)
    from backend.app.v5_inference import ApprovedModelRegistry
    app.state.model_registry = ApprovedModelRegistry(app.state.platform_store, catalog_path=client.catalog)
    with TestClient(app) as restarted:
        saved = restarted.get('/api/v5/inference/'+original['id'])
        assert saved.status_code == 200
        assert saved.json() == original
        history = restarted.get('/api/v5/inference',params={'dataset_id':client.dataset['id']})
        assert history.json() == {'items':[original]}
        repeated = restarted.post('/api/v5/inference/batch',json={'dataset_id':client.dataset['id'],'limit':2}).json()
        assert repeated['model'] == original['model']
        assert repeated['items'] == original['items']


def test_constant_accepts_empty_features_but_phase_requires_inputs(client):
    dataset = client.app.state.project_registry('local').register_bytes(b'nct_id,title\nNO-FEATURES,Empty protocol\n','minimal.csv')
    response = client.post('/api/v5/inference/batch',json={'dataset_id':dataset['id']})
    assert response.status_code == 201
    assert response.json()['summary']['available'] == 1
    response = client.post('/api/v5/inference/batch',json={'dataset_id':dataset['id'],'task':'phase'})
    assert response.status_code == 422
    assert 'schema' in response.text.lower() or 'feature' in response.text.lower()


def test_candidate_requires_owner_approval_and_does_not_replace_active(client):
    before = client.get('/api/v5/models').json()['active']['duration']
    model_id = candidate(client)
    assert batch(client,model_id=model_id).status_code == 409
    assert client.post('/api/v5/models/'+model_id+'/activate',json={'notes':'Unapproved'}).status_code == 409
    approved = client.post('/api/v5/models/'+model_id+'/approve',json={'notes':'Reviewed retrospective metrics and limitations','research_only_acknowledged':True})
    assert approved.status_code == 200, approved.text
    assert client.get('/api/v5/models').json()['active']['duration'] == before
    active = client.post('/api/v5/models/'+model_id+'/activate',json={'notes':'Research evaluation'})
    assert active.status_code == 200, active.text
    assert batch(client).json()['model']['id'] == model_id
    assert client.post('/api/v5/models/'+before+'/activate',json={'notes':'Rollback'}).status_code == 200
    assert batch(client).json()['model']['id'] == before


def test_active_remains_usable_while_separate_candidate_trains(client):
    registry = client.app.state.project_registry('local')
    registry.save_experiment({'id':'b'*32,'task':'duration','status':'running','dataset_id':client.dataset['id'],
        'dataset_sha256':client.dataset['sha256'],'created_at':'2026-10-09T00:00:00Z'})
    result = batch(client)
    assert result.status_code == 201
    assert result.json()['summary']['available'] == 2


def test_digest_mismatch_fails_closed_before_joblib_load(client, monkeypatch):
    model_id = candidate(client)
    approved = client.post('/api/v5/models/'+model_id+'/approve',json={'notes':'Research review','research_only_acknowledged':True})
    assert approved.status_code == 200, approved.text
    path = client.app.state.project_registry('local').artifact_path('a'*32)/'models.joblib'
    path.write_bytes(path.read_bytes()+b'tampered')
    import joblib
    monkeypatch.setattr(joblib,'load',lambda *args,**kw:pytest.fail('Changed artifact must not deserialize'))
    assert batch(client,model_id=model_id).status_code == 409


def test_pretrial_missing_or_late_timestamps_block_rows(client):
    response = batch(client,mode='pretrial')
    assert response.status_code == 201, response.text
    assert response.json()['summary']['blocked'] == 2
    assert all(i['prediction'] is None for i in response.json()['items'])
    assert 'timestamp' in json.dumps(response.json()).lower()


def test_nonowner_cannot_approve_or_activate(client):
    model_id = candidate(client)
    client.app.state.platform_store.execute("UPDATE v5_members SET role='researcher' WHERE project_id='local'")
    assert client.post('/api/v5/models/'+model_id+'/approve',json={'notes':'Denied','research_only_acknowledged':True}).status_code == 403
    assert client.post('/api/v5/models/bundled-duration-test/activate',json={'notes':'Denied'}).status_code == 403
    assert batch(client).status_code == 201


def test_fixture_inference_and_unapproved_unsafe_model_paths_rejected(client):
    assert client.post('/api/v5/inference/batch',json={'dataset_id':'sample-fixture'}).status_code == 422
    assert batch(client,model_id='../../external.joblib').status_code == 422
    assert batch(client,model_path='/tmp/untrusted.joblib').status_code == 422


def test_phase_model_is_selected_for_phase_objective(client):
    result = batch(client,task='phase')
    assert result.status_code == 201, result.text
    data = result.json()
    assert data['model']['task'] == 'phase'
    assert data['items'][0]['prediction']['predicted_phase']
    assert sum(data['items'][0]['prediction']['class_probabilities'].values()) == pytest.approx(1)
    assert batch(client,task='phase',model_id='bundled-duration-test').status_code == 422


def test_model_catalog_reports_real_heldout_metrics_and_validation_selection(client):
    result = client.get('/api/v5/models').json()
    duration = next(m for m in result['items'] if m['task']=='duration')
    manifest = json.loads((PROJECT_ROOT/'examples/starter-duration-v4/manifest.json').read_text())
    expected = min(manifest['models'],key=lambda name:manifest['models'][name]['metrics']['validation']['regression']['mae'])
    assert duration['branch'] == expected
    assert duration['validation_metrics'] == manifest['models'][expected]['metrics']['validation']
    assert duration['test_metrics'] == manifest['models'][expected]['metrics']['test']
    assert duration['approval_scope'] == 'research_only'


def test_legacy_research_predictions_use_approved_saved_artifact(client, monkeypatch):
    from sklearn.pipeline import Pipeline
    monkeypatch.setattr(Pipeline,'fit',forbid_fit)
    registry = client.app.state.project_registry('local')
    from backend.app.services.prediction_service import predict
    from backend.app.services.phase_service import predict_phase_for_dataset
    row = registry.frame(client.dataset['id']).iloc[0].to_dict()
    assert predict(row,client.dataset,registry)['status'] == 'available'
    assert predict_phase_for_dataset(row,client.dataset,registry)['status'] == 'available'
    assert registry.list_experiments() == []


def test_strict_pretrial_rejects_late_feature_and_accepts_complete_supplied_timestamps(client):
    service = client.app.state.model_registry
    registry = client.app.state.project_registry('local')
    resolved = service.resolve('local',registry,task='phase')
    row = registry.frame(client.dataset['id']).iloc[0].to_dict()
    row['prediction_as_of'] = '1900-01-01'
    row['start_date'] = '2000-01-01'
    fields = resolved['manifest']['features']
    for field in fields.get('numeric',[])+fields.get('categorical',[])+fields.get('text',[]):
        row[field+'_available_at'] = '1899-12-01'
    good = service.infer_rows('local',registry,[row],client.dataset,mode='pretrial',task='phase')
    assert good['summary']['available'] == 1
    row['enrollment_available_at'] = '2050-01-01'
    # Pick an actually consumed, present field for any validation-selected mode.
    mode = resolved['manifest']['models'][resolved['branch']].get('input_mode')
    if mode == 'text':
        row['title_available_at'] = '2050-01-01'
    blocked = service.infer_rows('local',registry,[row],client.dataset,mode='pretrial',task='phase')
    assert blocked['summary']['blocked'] == 1
    assert 'later than' in str(blocked['items'][0]['availability_warnings'])


def test_untrusted_candidate_metrics_fail_approval_without_switch(client):
    model_id = candidate(client)
    registry = client.app.state.project_registry('local')
    path = registry.artifact_path('a'*32)/'manifest.json'
    manifest = json.loads(path.read_text())
    for branch in manifest['models'].values():
        branch['metrics']['test']['regression']['rmse'] = None
    path.write_text(json.dumps(manifest))
    result = client.post('/api/v5/models/'+model_id+'/approve',json={'notes':'Must fail incomplete metrics','research_only_acknowledged':True})
    assert result.status_code == 422, result.text
    assert batch(client).json()['summary']['available'] == 2


def test_activated_candidate_survives_process_restart(client):
    model_id = candidate(client)
    assert client.post('/api/v5/models/'+model_id+'/approve',json={'notes':'Research review','research_only_acknowledged':True}).status_code == 200
    assert client.post('/api/v5/models/'+model_id+'/activate',json={'notes':'Research activation'}).status_code == 200
    from backend.app.v5_inference import ApprovedModelRegistry
    app = create_app(client.app.state.settings)
    app.state.model_registry = ApprovedModelRegistry(app.state.platform_store,catalog_path=client.catalog)
    with TestClient(app) as other:
        assert other.get('/api/v5/models').json()['active']['duration'] == model_id
        result = other.post('/api/v5/inference/batch',json={'dataset_id':client.dataset['id'],'limit':1})
        assert result.status_code == 201
        assert result.json()['model']['id'] == model_id


def test_batches_and_candidate_ids_are_project_scoped(tmp_path):
    settings = config(tmp_path).model_copy(update={'auth_mode':'session','setup_token':'inference-test-setup-token'})
    with TestClient(create_app(settings)) as client:
        setup = client.post('/api/v5/auth/setup',json={'email':'inference@example.org','password':'a sufficient test password',
            'name':'Inference owner','setup_token':'inference-test-setup-token'})
        assert setup.status_code == 201, setup.text
        project = client.post('/api/v5/projects',json={'name':'First scope'}).json()
        client.headers['X-Project-ID'] = project['id']
        frame = pd.read_csv(PROJECT_ROOT/'data/starter/trials.csv').head(2)
        client.dataset = client.app.state.project_registry(project['id']).register_bytes(frame.to_csv(index=False).encode(),'query.csv')
        response = batch(client)
        assert response.status_code == 201, response.text
        result = response.json()
        model_id = candidate(client,project_id=project['id'])
        other = client.post('/api/v5/projects',json={'name':'Other scope'}).json()
        client.headers['X-Project-ID'] = other['id']
        assert client.get('/api/v5/inference/'+result['id']).status_code == 404
        assert client.get('/api/v5/inference').json()['items'] == []
        assert batch(client).status_code == 404
        assert client.post('/api/v5/models/'+model_id+'/approve',json={'notes':'Cross project access','research_only_acknowledged':True}).status_code == 404


def test_real_v5_release_serves_immediately_without_fitting(tmp_path, monkeypatch):
    from sklearn.pipeline import Pipeline
    monkeypatch.setattr(Pipeline,'fit',forbid_fit)
    app = create_app(config(tmp_path))
    with TestClient(app) as client:
        catalog = client.get('/api/v5/models').json()
        assert set(catalog['active'].values()) == {'bundled-duration-v5','bundled-phase-v5'}
        source_hash = hashlib.sha256((PROJECT_ROOT/'data/starter/trials.csv').read_bytes()).hexdigest()
        historical=[model for model in catalog['items'] if model['id'].startswith('bundled-')]
        assert len(historical)==2
        assert all(model['training_dataset']['sha256'] == source_hash for model in historical)
        assert all(model['training_dataset']['id'] is None for model in historical)
        reference=[model for model in catalog['items'] if model['id'].startswith('registry-')]
        assert {model['id'] for model in reference}=={'registry-duration-v5205','registry-phase-v5205','registry-phase-refinement-v5205'}
        assert all(model['training_dataset']['sha256'] != source_hash for model in reference)
        frame = pd.read_csv(PROJECT_ROOT/'data/starter/trials.csv').head(1)
        frame['nct_id'] = 'NEW-V5-UPLOAD'
        dataset = app.state.project_registry('local').register_bytes(frame.to_csv(index=False).encode(),'new.csv')
        for task in ('duration','phase'):
            response = client.post('/api/v5/inference/batch',json={'dataset_id':dataset['id'],'task':task,'limit':1})
            assert response.status_code == 201, response.text
            assert response.json()['summary']['available'] == 1


@pytest.mark.parametrize('field,value',[
    ('start_date','January 2000'),
    ('start_date','2000-01'),
    ('prediction_as_of','1999'),
    ('prediction_as_of',0),
    ('title_available_at','December 1899'),
    ('title_available_at','1899-12'),
])
def test_strict_pretrial_rejects_ambiguous_or_partial_chronology_before_load(client,monkeypatch,field,value):
    service = client.app.state.model_registry
    registry = client.app.state.project_registry('local')
    row = registry.frame(client.dataset['id']).iloc[0].to_dict()
    # Phase consumes title and numeric/text features, independent of duration
    # selection. No ambiguous date may be inferred as an exact calendar day.
    resolved = service.resolve('local',registry,task='phase')
    row.update(prediction_as_of='1900-01-01',start_date='2000-01-01')
    for feature in resolved['manifest']['features']['numeric']+resolved['manifest']['features']['text']:
        row[feature+'_available_at'] = '1899-12-01'
    row[field] = value
    import joblib
    monkeypatch.setattr(joblib,'load',lambda *args,**kwargs:pytest.fail('Blocked chronology must not deserialize'))
    result = service.infer_rows('local',registry,[row],client.dataset,task='phase',mode='pretrial')
    assert result['summary'] == {'requested':1,'available':0,'blocked':1,'unavailable':0}
    assert result['items'][0]['prediction'] is None
