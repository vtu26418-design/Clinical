"""v5.2.0.2 evidence APIs: actual source aggregates and saved-model outputs."""
from __future__ import annotations

import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from .schemas_v4 import DatasetId, ScenarioRequest, StudyId
from .v4_routes import SafeValidationRoute
from .services.cohort_graphs import GRAPH_IDS, GRAPH_TYPES, aggregate_graphs, recruitment_summary
from .services.data_service import json_clean
from .services.prediction_service import predict
from .services.research_workspace import ResearchWorkspace, ResearchWorkspaceError
from .services.shap_adapter import explain_prediction
from .services.visualization_service import pipeline_status, study_visualization

LOGGER = logging.getLogger(__name__)

# The compatibility endpoint uses the identical source-bound research schema.
WhatIfRequest = ScenarioRequest


class SHAPRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: DatasetId
    nct_id: StudyId
    model_name: str = Field(default='recommended', min_length=1, max_length=100)


class GraphSelectionRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    dataset_id: DatasetId
    graphs: list[str] = Field(max_length=30)
    phase: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, max_length=80)


def attach_v521_routes(app, registry, config):
    service = getattr(app.state, 'research_workspace', None) or ResearchWorkspace(registry)
    app.state.research_workspace = service

    def require_token(authorization: str | None = Header(default=None)):
        if config.api_bearer_token:
            expected = f'Bearer {config.api_bearer_token}'.encode('utf-8')
            supplied = (authorization or '').encode('utf-8')
            if not hmac.compare_digest(supplied, expected):
                raise HTTPException(401, 'A valid API bearer token is required.', headers={'WWW-Authenticate': 'Bearer'})

    router = APIRouter(prefix='/api/v1', dependencies=[Depends(require_token)],
                       tags=['Evidence'], route_class=SafeValidationRoute)

    def dataset(dataset_id):
        value = registry.get_dataset(dataset_id)
        if value is None:
            raise HTTPException(404, 'Dataset not found.')
        return value

    def frame(dataset_id):
        dataset(dataset_id)
        try:
            return registry.frame(dataset_id)
        except (OSError, ValueError, KeyError):
            raise HTTPException(503, 'Dataset files are unavailable.') from None

    def run(operation):
        try:
            return json_clean(operation())
        except ResearchWorkspaceError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        except HTTPException:
            raise
        except Exception:
            LOGGER.exception('Evidence operation failed.')
            raise HTTPException(503, 'Evidence is temporarily unavailable. Check source storage and saved artifacts.') from None

    @router.post('/whatif')
    def whatif(req: ScenarioRequest):
        return run(lambda: service.create_scenario(service.snapshot(req.dataset_id, req.nct_id), req))

    @router.get('/model-branches')
    def model_branches():
        resolver = getattr(registry, 'approved_model_resolver', None)
        if resolver is None:
            return {'items': [], 'status': 'unavailable', 'reason': 'An approved project model is required.'}
        try:
            approved = resolver(task='duration', model_name='recommended')
            models = approved['manifest'].get('models', {})
            return {'status': 'available', 'model_id': approved['id'], 'recommended': approved['branch'],
                    'items': [{'id': name, 'label': value.get('display_name', name),
                               'input_mode': value.get('input_mode'), 'family': value.get('family')}
                              for name, value in models.items()]}
        except HTTPException:
            return {'items': [], 'status': 'unavailable', 'reason': 'No compatible approved duration model is available.'}

    @router.post('/explain')
    def explain(req: SHAPRequest):
        def operation():
            snapshot = service.snapshot(req.dataset_id, req.nct_id)
            prediction = predict(snapshot.study, snapshot.dataset, registry, req.model_name)
            return {'nct_id': req.nct_id, 'dataset_id': req.dataset_id,
                    'model_name': prediction.get('model_name'), 'prediction': prediction,
                    'provenance': snapshot.provenance, **explain_prediction(prediction, snapshot.study)}
        return run(operation)

    @router.post('/assistant/feedback', deprecated=True)
    def legacy_feedback():
        raise HTTPException(410, 'Use project-scoped /api/v5/messages/{message_id}/feedback for an actual saved assistant message.')

    @router.get('/graph-types')
    def graph_types():
        return {'graph_types': GRAPH_TYPES}

    @router.post('/overview/graphs')
    def graphs(req: GraphSelectionRequest):
        unknown = sorted(set(req.graphs) - GRAPH_IDS)
        if unknown:
            raise HTTPException(422, {'message': 'Unknown graph type.', 'graphs': unknown})
        def operation():
            ds = dataset(req.dataset_id)
            df = frame(req.dataset_id)
            source_rows = len(df)
            if req.phase:
                from src.clinical_trial_intelligence.research import normalize_design_phase
                df = df[df['phase'].map(normalize_design_phase).eq(normalize_design_phase(req.phase))]
            if req.status:
                df = df[df['status'].astype(str).str.casefold().eq(req.status.casefold())]
            experiments = registry.list_experiments(req.dataset_id)
            resolver = getattr(registry, 'approved_model_resolver', None)
            if resolver is not None:
                try:
                    approved = resolver(task='duration', model_name='recommended')
                    manifest = approved['manifest']
                    experiments = [*experiments, {'id': approved['id'], 'status': 'completed', 'task': 'duration',
                                                  'manifest': manifest,
                                                  'dataset_sha256': next((manifest.get('source_metadata', {}).get(key)
                                                                          for key in ('sha256', 'source_sha256', 'canonical_sha256')
                                                                          if manifest.get('source_metadata', {}).get(key)), None)}]
                except Exception:
                    pass
            return aggregate_graphs(df, list(dict.fromkeys(req.graphs)), dataset=ds, source_rows=source_rows,
                                    filters={'phase': req.phase, 'status': req.status}, experiments=experiments)
        return run(operation)

    @router.get('/recruitment/{dataset_id}')
    def recruitment(dataset_id: DatasetId):
        return run(lambda: {'dataset_id': dataset_id, **recruitment_summary(frame(dataset_id))})

    @router.get('/pipeline-status')
    def pipeline(dataset_id: DatasetId | None = None):
        if dataset_id:
            dataset(dataset_id)
        return run(lambda: pipeline_status(registry.list_experiments(dataset_id)))

    @router.get('/visualizations/study')
    def visualizations(dataset_id: DatasetId, nct_id: StudyId,
                       model_name: str = Query(default='recommended', min_length=1, max_length=80, pattern=r'^[a-z0-9_]+$')):
        def operation():
            snapshot = service.snapshot(dataset_id, nct_id)
            workspace = service.workspace(snapshot)
            if model_name != 'recommended':
                workspace['duration'] = predict(snapshot.study, snapshot.dataset, registry, model_name)
            return study_visualization(workspace)
        return run(operation)

    app.include_router(router)
    return router
