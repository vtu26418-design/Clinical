"""Clinical Trial Intelligence Workbench API (local-first research software)."""
from __future__ import annotations

import csv
import hmac
import html
import io
import json
import threading
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

import pandas as pd
from threadpoolctl import threadpool_limits
from fastapi import APIRouter, BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Settings, settings, PROJECT_ROOT
from .schemas import AssistantRequest, ClinicalTrialsImportRequest, ExperimentRequest, PredictionRequest, PhasePredictionRequest
from .services.clinicaltrials_service import RegistryImportError, fetch_trials
from .services.data_service import DatasetRegistry, DatasetValidationError, SAMPLE_ID, json_clean, now
from .services.assistant_service import AssistantUnavailable, assist, assistant_status
from .services.pci_service import METHODOLOGY, calculate_pci, calculate_pci_details
from .services.prediction_service import predict
from .services.phase_service import predict_phase_for_dataset
from .services.training_preflight import preflight


def create_research_app(config: Settings | None = None, *, training_slot=None) -> FastAPI:
    config = config or settings
    registry = DatasetRegistry(config)

    @asynccontextmanager
    async def lifespan(_app):
        # The documented single-process worker cannot resume Python jobs after
        # a restart. Preserve their history and make that terminal state visible.
        for record in registry.list_experiments():
            if record['status'] in ('queued', 'running'):
                record.update(status='failed', completed_at=now(), error='Server restarted before training completed. Start a new experiment to retry.')
                registry.save_experiment(record)
        try:
            yield
        finally:
            if registry.engine is not None:
                registry.engine.dispose()

    app = FastAPI(title='Clinical Trial Intelligence API', version='5.2.0.2', description='Research decision support; not clinical or regulatory advice.', lifespan=lifespan)
    app.state.settings = config
    app.state.registry = registry
    training_slot = training_slot or threading.BoundedSemaphore(1)
    app.add_middleware(CORSMiddleware, allow_origins=[value.strip() for value in config.cors_origins.split(',') if value.strip()], allow_credentials=False, allow_methods=['GET', 'POST'], allow_headers=['Authorization', 'Content-Type'])

    def require_token(authorization: str | None = Header(default=None)):
        if config.api_bearer_token and (not authorization or not hmac.compare_digest(authorization, f'Bearer {config.api_bearer_token}')):
            raise HTTPException(401, 'A valid API bearer token is required.', headers={'WWW-Authenticate': 'Bearer'})

    api = APIRouter(prefix='/api/v1', dependencies=[Depends(require_token)])

    def dataset(dataset_id: str):
        value = registry.get_dataset(dataset_id)
        if value is None:
            raise HTTPException(404, 'Dataset not found.')
        return value

    def frame(dataset_id: str):
        dataset(dataset_id)
        try:
            return registry.frame(dataset_id)
        except (OSError, ValueError, KeyError) as exc:
            raise HTTPException(503, 'Dataset files are unavailable. Restore server storage from backup.') from exc

    def records(dataset_id: str):
        return json_clean(frame(dataset_id).to_dict(orient='records'))

    def row_for(dataset_id: str, nct_id: str):
        df = frame(dataset_id)
        rows = df[df['nct_id'].astype(str) == nct_id]
        if rows.empty:
            raise HTTPException(404, 'Study not found in the selected dataset.')
        return json_clean(rows.iloc[0].to_dict())

    def summary(row: dict):
        score, category, _ = calculate_pci(row)
        return {**row, 'pci': score, 'complexity': category, 'prolonged_risk': None}

    def source_metadata(value: dict):
        return {'dataset_id': value['id'], 'sha256': value['sha256'], 'source_name': value['source'], 'fixture': value['is_fixture'], 'baseline_provenance': False, 'snapshot': value['provenance']}

    @app.get('/api/v1/health')
    def health():
        key_configured = bool(config.openai_api_key.strip())
        routing = assistant_status(config)
        return {'status': 'ok', 'version': '5.2.0.2', 'ai_provider': routing['selected_label'] if routing['enabled'] else 'disabled', 'openai_configured': key_configured, 'assistant_enabled': routing['enabled'], 'assistant': routing, 'sample_data': True, 'default_dataset_id': SAMPLE_ID, 'auth_required': bool(config.api_bearer_token), 'database': 'postgresql', 'configuration': {'storage_ready': registry.root.is_dir(), 'openai_key_present': key_configured, 'openai_model': config.openai_model, 'remote_auth_configured': bool(config.api_bearer_token)}}

    @api.get('/readiness')
    def readiness(dataset_id: str = SAMPLE_ID):
        value = dataset(dataset_id)
        df = frame(dataset_id)
        metadata = source_metadata(value)
        return {'duration': preflight(df, metadata, 'duration', config.max_training_rows),
                'phase': preflight(df, metadata, 'phase', config.max_training_rows),
                'starter_available': (PROJECT_ROOT / 'data/starter/trials.csv').is_file(),
                'openai_configured': bool(config.openai_api_key.strip()),
                'assistant_enabled': assistant_status(config)['enabled'],
                'storage_ready': registry.root.is_dir()}

    @api.post('/datasets/starter', status_code=201)
    def load_starter():
        existing = registry.get_dataset('clinicaltrials-starter-v3')
        if existing:
            return existing
        path = PROJECT_ROOT / 'data/starter/trials.csv'
        if not path.is_file():
            raise HTTPException(404, 'Starter data is absent. Run scripts/download_starter_data.py or import your own cohort.')
        provenance = json.loads((path.parent / 'metadata.json').read_text(encoding='utf-8'))
        try:
            return registry.register_bytes(path.read_bytes(), 'trials.csv', name='ClinicalTrials.gov starter cohort · v3',
                source='ClinicalTrials.gov v2 frozen starter subset', provenance=provenance, dataset_id='clinicaltrials-starter-v3')
        except (DatasetValidationError, RuntimeError) as exc:
            raise HTTPException(422, 'Starter data could not be loaded. Check the bundled snapshot and validation report.') from exc

    @api.get('/datasets')
    def datasets():
        return {'items': registry.list_datasets(), 'active_default': SAMPLE_ID}

    @api.post('/datasets/upload', status_code=201)
    async def upload_dataset(file: UploadFile = File(...), name: str | None = Form(default=None, max_length=120)):
        raw = await file.read(config.max_upload_bytes + 1)
        await file.close()
        if len(raw) > config.max_upload_bytes:
            raise HTTPException(413, f'Upload exceeds {config.max_upload_bytes} bytes.')
        try:
            return registry.register_bytes(raw, file.filename or '', name=name)
        except DatasetValidationError as exc:
            raise HTTPException(422, {'message': str(exc), 'errors': exc.errors}) from exc
        except (OSError, RuntimeError) as exc:
            raise HTTPException(503, 'Dataset could not be saved. Check server storage availability.') from exc

    @api.post('/datasets/import/clinicaltrials', status_code=201)
    def import_clinicaltrials(req: ClinicalTrialsImportRequest):
        try:
            raw, df, provenance = fetch_trials(req.query, req.max_studies, config.max_upload_bytes)
            return registry.register_bytes(raw, 'clinicaltrials-v2.json', name=req.name or f'ClinicalTrials.gov: {req.query}', source='ClinicalTrials.gov v2', provenance=provenance, canonical_frame=df)
        except RegistryImportError as exc:
            raise HTTPException(502, str(exc)) from exc
        except DatasetValidationError as exc:
            raise HTTPException(422, {'message': str(exc), 'errors': exc.errors}) from exc
        except (OSError, RuntimeError) as exc:
            raise HTTPException(503, 'Dataset could not be saved. Check server storage availability.') from exc

    @api.get('/studies')
    def studies(dataset_id: str = SAMPLE_ID, q: str = Query('', max_length=120), phase: str | None = Query(None, max_length=80), status: str | None = Query(None, max_length=80), sort_by: Literal['nct_id', 'title', 'phase', 'status', 'enrollment', 'pci', 'start_date'] = 'nct_id', sort_dir: Literal['asc', 'desc'] = 'asc', offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
        df = frame(dataset_id)
        if q:
            mask = df['nct_id'].astype(str).str.contains(q, case=False, regex=False, na=False) | df['title'].astype(str).str.contains(q, case=False, regex=False, na=False)
            df = df[mask]
        if phase:
            df = df[df['phase'].str.casefold() == phase.casefold()]
        if status:
            df = df[df['status'].str.casefold() == status.casefold()]
        if sort_by == 'pci':
            df = df.assign(pci=df.apply(lambda row: calculate_pci(row.to_dict())[0], axis=1))
        df = df.sort_values(sort_by, ascending=sort_dir == 'asc', na_position='last', kind='stable')
        rows = [summary(row) for row in json_clean(df.iloc[offset:offset + limit].to_dict(orient='records'))]
        # Listing remains a fast descriptive table; actual predictions and their
        # provenance are returned on study detail, never approximated here.
        return {'items': rows, 'total': len(df), 'offset': offset, 'limit': limit}

    @api.get('/studies/{nct_id}')
    def study(nct_id: str, dataset_id: str = SAMPLE_ID):
        value = dataset(dataset_id)
        row = row_for(dataset_id, nct_id)
        score, category, components = calculate_pci(row)
        return {'study': row, 'pci': calculate_pci_details(row), 'prediction': json_clean(predict(row, value, registry))}

    @api.get('/pci/{nct_id}')
    def pci(nct_id: str, dataset_id: str = SAMPLE_ID):
        row = row_for(dataset_id, nct_id)
        score, category, components = calculate_pci(row)
        return {'nct_id': nct_id, 'pci': score, 'category': category, 'components': components, 'methodology': METHODOLOGY}

    @api.post('/predictions')
    def prediction(req: PredictionRequest):
        value = dataset(req.dataset_id)
        return {'nct_id': req.nct_id, **json_clean(predict(row_for(req.dataset_id, req.nct_id), value, registry, req.model_name))}

    @api.post('/phase-predictions')
    def phase_prediction(req: PhasePredictionRequest):
        value = dataset(req.dataset_id)
        return json_clean(predict_phase_for_dataset(row_for(req.dataset_id, req.nct_id), value, registry))

    @api.get('/overview')
    def overview(dataset_id: str = SAMPLE_ID):
        value = dataset(dataset_id)
        df = frame(dataset_id)
        scores = df.apply(lambda row: calculate_pci(row.to_dict())[0], axis=1)
        # Confirm a usable prediction through the same compatibility/fallback
        # path as study detail; mere artifact file presence is insufficient.
        available = predict(df.iloc[0].to_dict(), value, registry).get('status') == 'available'
        return json_clean({'dataset': value, 'total_studies': len(df), 'median_pci': round(float(scores.median()), 2), 'phase_counts': df['phase'].fillna('Not reported').value_counts().to_dict(), 'status_counts': df['status'].fillna('Unknown').value_counts().to_dict(), 'enrollment_total': float(pd.to_numeric(df['enrollment'], errors='coerce').sum()), 'quality': value['quality'], 'predictions_available': available, 'pci_distribution': [{'nct_id': row['nct_id'], 'title': row['title'], 'pci': score} for row, score in zip(json_clean(df[['nct_id','title']].head(100).to_dict(orient='records')), scores.head(100).tolist())], 'methodology': METHODOLOGY})

    def run_training(record: dict, df: pd.DataFrame, metadata: dict):
        record.update(status='running', started_at=now())
        try:
            registry.save_experiment(record)
            output = registry.artifact_path(record['id'])
            # Bound native BLAS/OpenMP work even if the operator bypasses the
            # launcher or this process already imported scientific libraries.
            with threadpool_limits(limits=1):
                if record.get('task') == 'phase':
                    from src.clinical_trial_intelligence.phase_model import train_phase_experiment
                    manifest = train_phase_experiment(df, output, source_metadata=metadata)
                else:
                    from src.clinical_trial_intelligence.research import ExperimentConfig, train_experiment
                    manifest = train_experiment(df, output, source_metadata=metadata,
                                                config=ExperimentConfig(enable_catboost=bool(record.get('enable_catboost', False))))
            metrics_path = output / ('phase_metrics.json' if record.get('task') == 'phase' else 'metrics.json')
            metrics = json.loads(metrics_path.read_text(encoding='utf-8')) if metrics_path.exists() else manifest.get('metrics', {})
            record.update(status='completed', completed_at=now(), manifest=manifest, metrics=metrics, error=None)
        except ValueError as exc:
            record.update(status='failed', completed_at=now(), error=str(exc)[:1200])
        except Exception:
            record.update(status='failed', completed_at=now(), error='Training failed. Inspect the local server logs and data quality; no predictions were published.')
            import logging
            logging.getLogger(__name__).exception('Experiment %s failed', record['id'])
        finally:
            try:
                registry.save_experiment(record)
            finally:
                training_slot.release()

    @api.get('/experiments')
    def experiments(dataset_id: str | None = None):
        if dataset_id:
            dataset(dataset_id)
        return {'items': registry.list_experiments(dataset_id)}

    def queue_experiment(req, background, task):
        value = dataset(req.dataset_id)
        df = frame(req.dataset_id)
        metadata = source_metadata(value)
        check = preflight(df, metadata, task, config.max_training_rows)
        if not check['ready']:
            raise HTTPException(422, check['reason'])
        if not training_slot.acquire(blocking=False):
            raise HTTPException(409, 'An experiment is already running on this server. Wait for it to finish.')
        record = {'id': uuid.uuid4().hex, 'task': task, 'dataset_id': value['id'], 'dataset_sha256': value['sha256'], 'status': 'queued', 'created_at': now(), 'error': None, 'metrics': None, 'manifest': None,
                  'enable_catboost': bool(getattr(req, 'enable_catboost', False)) if task == 'duration' else False}
        try:
            registry.save_experiment(record)
            background.add_task(run_training, record.copy(), df, metadata)
        except Exception:
            training_slot.release()
            raise
        return record

    @api.post('/experiments', status_code=202)
    def launch_experiment(req: ExperimentRequest, background: BackgroundTasks):
        return queue_experiment(req, background, 'duration')

    @api.post('/phase-experiments', status_code=202)
    def launch_phase_experiment(req: ExperimentRequest, background: BackgroundTasks):
        return queue_experiment(req, background, 'phase')

    @api.get('/experiments/{experiment_id}/files/{filename}')
    def experiment_file(experiment_id: str, filename: str):
        run = registry.get_experiment(experiment_id)
        if not run or run['status'] != 'completed':
            raise HTTPException(404, 'Completed experiment not found.')
        allowed = {'manifest.json', 'metrics.json', 'held_out_predictions.csv', 'cohort_exclusions.csv', 'temporal_exclusions.csv',
                   'phase_manifest.json', 'phase_metrics.json', 'phase_held_out_predictions.csv', 'phase_cohort_exclusions.csv'}
        if filename not in allowed:
            raise HTTPException(404, 'Report not found.')
        directory = registry.artifact_path(experiment_id)
        path = directory / filename
        if directory.is_symlink() or path.is_symlink() or not path.is_file():
            raise HTTPException(404, 'Report not found.')
        if filename.endswith('.csv'):
            rows = list(csv.reader(io.StringIO(path.read_text(encoding='utf-8'))))
            stream = io.StringIO(newline='')
            csv.writer(stream).writerows([[safe_cell(cell) for cell in row] for row in rows])
            return Response(stream.getvalue(), media_type='text/csv', headers={'Content-Disposition': f'attachment; filename="{filename}"'})
        return FileResponse(path, filename=filename, media_type='application/json')

    @api.get('/experiments/{experiment_id}')
    def experiment(experiment_id: str):
        result = registry.get_experiment(experiment_id)
        if result is None:
            raise HTTPException(404, 'Experiment not found.')
        return result

    @api.post('/assistant')
    def assistant(req: AssistantRequest):
        value = dataset(req.dataset_id)
        context = {'dataset': {'name': value['name'], 'source': value['source'], 'rows': value['row_count'], 'is_fixture': value['is_fixture'], 'warnings': value['quality']['warnings']}, 'pci_methodology': METHODOLOGY}
        if req.nct_id:
            selected = study(req.nct_id, req.dataset_id)
            context['selected_study'] = selected
        try:
            result = assist(config, req.message, context, req.provider)
        except AssistantUnavailable as exc:
            raise HTTPException(503, str(exc)) from exc
        return result

    def safe_cell(value):
        if isinstance(value, str) and value.lstrip(' \t\r\n').startswith(('=', '+', '-', '@')):
            return "'" + value
        return value

    @api.get('/exports/studies.csv')
    def export_csv(dataset_id: str = SAMPLE_ID):
        rows = [summary(row) for row in records(dataset_id)]
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows({key: safe_cell(value) for key, value in row.items()} for row in rows)
        return Response(content='\ufeff' + stream.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename="clinical-trial-studies.csv"', 'X-Content-Type-Options': 'nosniff'})

    @api.get('/exports/studies.json')
    def export_json(dataset_id: str = SAMPLE_ID):
        return Response(content=json.dumps({'dataset': dataset(dataset_id), 'studies': records(dataset_id)}, ensure_ascii=False, allow_nan=False), media_type='application/json', headers={'Content-Disposition': 'attachment; filename="clinical-trial-studies.json"'})

    @api.get('/exports/report.html', response_class=HTMLResponse)
    def export_report(dataset_id: str = SAMPLE_ID):
        value = dataset(dataset_id)
        rows = [summary(row) for row in records(dataset_id)]
        escape = lambda v: html.escape(str(v), quote=True)
        cells = ''.join('<tr>' + ''.join(f'<td>{escape(row.get(key, ""))}</td>' for key in ('nct_id', 'title', 'phase', 'status', 'pci', 'complexity')) + '</tr>' for row in rows)
        content = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Clinical Trial Intelligence Report</title><style>body{{font:15px system-ui;max-width:1100px;margin:40px auto;color:#142d41}}table{{border-collapse:collapse;width:100%}}th,td{{padding:9px;text-align:left;border-bottom:1px solid #dce3e7}}small{{color:#536474}}</style></head><body><h1>Clinical Trial Intelligence Report</h1><h2>{escape(value['name'])}</h2><p>{'SOFTWARE TEST FIXTURES — not research evidence.' if value['is_fixture'] else 'Research dataset — assess provenance and quality before interpretation.'}</p><p>Source: {escape(value['source'])}; records: {len(rows)}; captured: {escape(value['created_at'])}</p><p><small>SHA-256: {escape(value['sha256'])}</small></p><p>{escape(METHODOLOGY)}</p><p>Model predictions are available separately only after compatible training. This descriptive report does not infer outcome probabilities.</p><table><thead><tr><th>Study ID</th><th>Title</th><th>Phase</th><th>Status</th><th>PCI</th><th>Complexity</th></tr></thead><tbody>{cells}</tbody></table><h2>Data quality</h2><ul>{''.join('<li>' + escape(warning) + '</li>' for warning in value['quality']['warnings'])}</ul><p>Research decision support only; not clinical or regulatory advice.</p></body></html>'''
        return HTMLResponse(content=content, headers={'Content-Disposition': 'attachment; filename="clinical-trial-report.html"', 'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'", 'X-Content-Type-Options': 'nosniff'})

    app.include_router(api)
    from .v4_routes import attach_v4_routes
    attach_v4_routes(app, registry, config)
    from .v521_routes import attach_v521_routes
    attach_v521_routes(app, registry, config)
    dist = config.path(config.frontend_dist)
    if dist.is_dir() and (dist / 'index.html').is_file():
        app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
    return app


def create_app(config: Settings | None = None) -> FastAPI:
    from .platform import create_app as create_platform_app
    return create_platform_app(config)


app = create_app()
