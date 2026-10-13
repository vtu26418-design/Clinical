"""Independent authenticated v4 research routes, attached before static files."""
from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from .schemas_v4 import DatasetId, ScenarioRequest, StudyId
from .services.research_workspace import ResearchWorkspace, ResearchWorkspaceError

LOGGER = logging.getLogger(__name__)


class SafeValidationRoute(APIRoute):
    """Never echo invalid non-finite JSON values in a validation response."""
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def safe_handler(request):
            try:
                return await handler(request)
            except RequestValidationError as exc:
                # FastAPI's default error includes the rejected input; raw JSON
                # NaN/Infinity then breaks strict JSON response serialization.
                detail = [{'loc': list(item['loc']), 'msg': item['msg'], 'type': item['type']}
                          for item in exc.errors()]
                return JSONResponse(status_code=422, content={'detail': detail})

        return safe_handler


def attach_v4_routes(app, registry, config):
    """Register /api/v1/research using the same server bearer configuration."""
    service = ResearchWorkspace(registry)
    app.state.research_workspace = service

    def require_token(authorization: str | None = Header(default=None)):
        if config.api_bearer_token:
            expected = f'Bearer {config.api_bearer_token}'.encode('utf-8')
            supplied = (authorization or '').encode('utf-8')
            if not hmac.compare_digest(supplied, expected):
                raise HTTPException(401, 'A valid API bearer token is required.', headers={'WWW-Authenticate': 'Bearer'})

    router = APIRouter(prefix='/api/v1/research', dependencies=[Depends(require_token)], tags=['Research'],
                       route_class=SafeValidationRoute)

    def run(operation):
        try:
            return operation()
        except ResearchWorkspaceError as exc:
            raise HTTPException(exc.status, str(exc)) from None
        except Exception:
            LOGGER.exception('Research workspace operation failed.')
            raise HTTPException(503, 'Research workspace is temporarily unavailable. Check local server storage and artifacts.') from None

    @router.get('/workspace')
    def workspace(dataset_id: DatasetId, nct_id: StudyId):
        return run(lambda: service.workspace(service.snapshot(dataset_id, nct_id)))

    @router.get('/similar')
    def similar(dataset_id: DatasetId, nct_id: StudyId, same_phase: bool = True,
                limit: Annotated[int, Query(ge=1, le=10)] = 5):
        return run(lambda: service.similar(service.snapshot(dataset_id, nct_id), same_phase, limit))

    @router.post('/scenarios')
    def scenario(request: ScenarioRequest):
        return run(lambda: service.create_scenario(service.snapshot(request.dataset_id, request.nct_id), request))

    @router.get('/scenarios')
    def scenarios(dataset_id: DatasetId, nct_id: StudyId):
        return run(lambda: service.scenarios(service.snapshot(dataset_id, nct_id)))

    @router.get('/evidence')
    def evidence(dataset_id: DatasetId, nct_id: StudyId):
        return run(lambda: service.evidence(service.snapshot(dataset_id, nct_id)))

    app.include_router(router)
    return service
