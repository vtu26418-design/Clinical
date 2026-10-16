from pathlib import Path
import shutil
from fastapi.testclient import TestClient
from backend.app.config import Settings
from backend.app.main import create_research_app


def api(tmp_path):
    return TestClient(create_research_app(Settings(storage_dir=str(tmp_path/'store'))))


def test_active_model_report_recomputes_bundled_evidence_and_downloads_html(tmp_path):
    with api(tmp_path) as client:
        response=client.get('/api/v1/model-analysis')
        assert response.status_code==200,response.text
        report=response.json()
        assert report['task']=='duration' and report['models']
        assert report['split_counts']['test']['n']==64
        page=client.get('/api/v1/model-analysis',params={'format':'html'})
        assert page.status_code==200 and 'text/html' in page.headers['content-type']
        assert 'attachment;' in page.headers['content-disposition']
        assert 'default-src' in page.headers['content-security-policy']
        assert 'RMSE' in page.text
        csv=client.get('/api/v1/model-analysis',params={'format':'csv'})
        assert csv.status_code==200 and 'model_name' in csv.text


def test_report_rejects_unknown_model_and_format_and_no_run(tmp_path):
    with api(tmp_path) as client:
        assert client.get('/api/v1/model-analysis',params={'model_id':'../private'}).status_code==404
        assert client.get('/api/v1/model-analysis',params={'format':'exe'}).status_code==422
        assert client.get('/api/v1/experiments/unknown/analysis').status_code==404


def test_project_run_report_reads_only_completed_local_run(tmp_path):
    app=create_research_app(Settings(storage_dir=str(tmp_path/'store')))
    registry=app.state.registry
    run_id='f'*32
    registry.save_experiment({'id':run_id,'status':'completed','task':'duration','dataset_id':'sample-fixture','created_at':'2026-10-16T00:00:00Z'})
    target=registry.artifact_path(run_id);target.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).resolve().parents[1]/'examples/starter-duration-v5'
    for name in ('manifest.json','metrics.json','held_out_predictions.csv'):
        shutil.copyfile(source/name,target/name)
    with TestClient(app) as client:
        response=client.get(f'/api/v1/experiments/{run_id}/analysis')
        assert response.status_code==200,response.text
        assert response.json()['split_counts']['test']['n']==64
        registry.save_experiment({'id':run_id,'status':'running','task':'duration','dataset_id':'sample-fixture','created_at':'2026-10-16T00:00:00Z'})
        assert client.get(f'/api/v1/experiments/{run_id}/analysis').status_code==404


def test_standalone_report_preserves_api_token_requirement(tmp_path):
    app=create_research_app(Settings(storage_dir=str(tmp_path/'store'),api_bearer_token='test-report-token'))
    with TestClient(app) as client:
        assert client.get('/api/v1/model-analysis').status_code==401
        assert client.get('/api/v1/experiments/unknown/analysis').status_code==401
        assert client.get('/api/v1/model-analysis',headers={'Authorization':'Bearer test-report-token'}).status_code==200
