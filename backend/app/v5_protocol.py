"""Project-bound protocol evidence, version comparison and human review."""
from __future__ import annotations
import json
import re
import uuid
from typing import Literal
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field
from .services.data_service import now
from .services.protocol_service import extract_document, availability_audit, compare_texts, domain_score


class TextProtocol(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=20, max_length=250_000)
    group_id: str | None = Field(default=None, max_length=64, pattern=r'^[a-zA-Z0-9_-]+$')


class Review(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['accepted', 'corrected', 'rejected']
    notes: str = Field(min_length=5, max_length=4000)
    fields: dict = Field(default_factory=dict, max_length=20)


class Availability(BaseModel):
    prediction_at: str = Field(max_length=40)
    feature_timestamps: dict[str, str | None] = Field(max_length=100)


class Rubric(BaseModel):
    scores: dict[str, float | None] = Field(max_length=7)
    weights: dict[str, float] = Field(max_length=7)


def attach_protocol_routes(app):
    store = app.state.platform_store
    store.execute('CREATE TABLE IF NOT EXISTS v5_protocols (id VARCHAR(64) PRIMARY KEY, project_id VARCHAR(64) NOT NULL, group_id VARCHAR(64) NOT NULL, title TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
    store.execute('CREATE TABLE IF NOT EXISTS v5_protocol_reviews (id VARCHAR(64) PRIMARY KEY, project_id VARCHAR(64) NOT NULL, protocol_id VARCHAR(64) NOT NULL, user_id VARCHAR(64) NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
    store.execute('CREATE INDEX IF NOT EXISTS v5_protocols_project ON v5_protocols(project_id,created_at)')
    router = APIRouter(prefix='/api/v5', tags=['Protocol evidence'])

    def get(pid, docid):
        records = store.execute('SELECT * FROM v5_protocols WHERE id=:id AND project_id=:pid', {'id': docid, 'pid': pid}, True)
        if not records:
            raise HTTPException(404, 'Protocol not found in this project.')
        value = records[0]
        payload = json.loads(value.pop('payload'))
        reviews = store.execute('SELECT * FROM v5_protocol_reviews WHERE protocol_id=:id AND project_id=:pid ORDER BY created_at DESC', {'id': docid, 'pid': pid}, True)
        result = {**value, **payload, 'reviews': [{**r, 'payload': json.loads(r['payload'])} for r in reviews]}
        if reviews:
            latest = json.loads(reviews[0]['payload'])
            result['review_status'] = latest['status']
            result['reviewed_features'] = {**result['features'], **latest['fields']}
        return result

    def save(req, title, raw, filename, group_id=None):
        project = app.state.require_project(req, roles={'owner', 'researcher'})
        user = app.state.current_user(req)
        if group_id:
            prior = store.execute('SELECT id FROM v5_protocols WHERE group_id=:gid AND project_id=:pid', {'gid': group_id, 'pid': project['id']}, True)
            if not prior:
                raise HTTPException(404, 'Version family not found in this project.')
        try:
            payload = extract_document(raw, filename)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        # Persist extracted evidence remotely when PostgreSQL is configured;
        # preserve original bytes in the project artifact volume.
        registry = app.state.project_registry(project['id'])
        directory = registry.root / 'protocols'
        directory.mkdir(exist_ok=True)
        document_id = uuid.uuid4().hex
        suffix = '.pdf' if filename.lower().endswith('.pdf') else '.txt'
        (directory / (document_id + suffix)).write_bytes(raw)
        payload['original_filename'] = filename.replace('\\', '/').split('/')[-1][:200]
        stamp = now()
        store.execute('INSERT INTO v5_protocols(id,project_id,group_id,title,created_at,payload) VALUES (:id,:pid,:gid,:title,:stamp,:payload)', {'id': document_id, 'pid': project['id'], 'gid': group_id or document_id, 'title': title, 'stamp': stamp, 'payload': json.dumps(payload, allow_nan=False)})
        app.state.audit(project['id'], user['id'], 'protocol.import', {'protocol_id': document_id, 'source_sha256': payload['source_sha256']})
        return get(project['id'], document_id)

    @router.get('/protocols')
    def protocols(req: Request):
        project = app.state.require_project(req)
        rows = store.execute('SELECT id FROM v5_protocols WHERE project_id=:pid ORDER BY created_at DESC', {'pid': project['id']}, True)
        result = []
        for row in rows[:200]:
            item = get(project['id'], row['id'])
            result.append({k: v for k, v in item.items() if k not in {'text', 'pages', 'evidence', 'reviews'}})
        return {'items': result}

    @router.post('/protocols/text', status_code=201)
    def text_protocol(req: Request, value: TextProtocol):
        return save(req, value.title, value.text.encode(), 'protocol.txt', value.group_id)

    @router.post('/protocols/upload', status_code=201)
    async def upload(req: Request, file: UploadFile = File(...), title: str = Form(..., min_length=1, max_length=180), group_id: str | None = Form(None)):
        app.state.require_project(req, roles={'owner', 'researcher'})
        raw = await file.read(8 * 1024 * 1024 + 1)
        await file.close()
        return save(req, title, raw, file.filename or '', group_id)

    @router.get('/protocols/compare')
    def compare(req: Request, older: str, newer: str):
        project = app.state.require_project(req)
        first, second = get(project['id'], older), get(project['id'], newer)
        return {**compare_texts(first['text'], second['text']), 'older': {'id': older, 'sha256': first['source_sha256']}, 'newer': {'id': newer, 'sha256': second['source_sha256']}}

    @router.get('/protocols/{docid}')
    def protocol(req: Request, docid: str):
        return get(app.state.require_project(req)['id'], docid)

    @router.post('/protocols/{docid}/review')
    def review(req: Request, docid: str, value: Review):
        project = app.state.require_project(req, roles={'owner', 'reviewer'})
        user = app.state.current_user(req)
        doc = get(project['id'], docid)
        allowed = {'phase', 'enrollment', 'number_of_arms', 'primary_outcomes', 'secondary_outcomes', 'criteria_count'}
        if not set(value.fields).issubset(allowed):
            raise HTTPException(422, 'Corrections must use documented phase/enrollment/arm/outcome/criteria fields.')
        for key, val in value.fields.items():
            if key == 'phase':
                if val not in {'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4', 'NA', 'Not reported'}:
                    raise HTTPException(422, 'Unsupported phase correction.')
            elif isinstance(val, bool) or not isinstance(val, int) or not 0 <= val <= 10_000_000:
                raise HTTPException(422, 'Count corrections must be finite non-negative integers.')
        if value.status == 'corrected' and not value.fields:
            raise HTTPException(422, 'Supply corrected fields with a corrected review.')
        record = value.model_dump()
        store.execute('INSERT INTO v5_protocol_reviews(id,project_id,protocol_id,user_id,created_at,payload) VALUES (:id,:pid,:doc,:uid,:stamp,:payload)', {'id': uuid.uuid4().hex, 'pid': project['id'], 'doc': docid, 'uid': user['id'], 'stamp': now(), 'payload': json.dumps(record, allow_nan=False)})
        app.state.audit(project['id'], user['id'], 'protocol.review', {'protocol_id': docid, 'status': value.status, 'source_sha256': doc['source_sha256']})
        return get(project['id'], docid)

    @router.post('/protocols/availability/audit')
    def audit(req: Request, value: Availability):
        app.state.require_project(req)
        try:
            return availability_audit(value.prediction_at, value.feature_timestamps)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @router.post('/protocols/complexity/rubric')
    def rubric(req: Request, value: Rubric):
        app.state.require_project(req)
        try:
            return domain_score(value.scores, value.weights)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    app.include_router(router)


def retrieve_project_evidence(app, project_id: str, query: str) -> list:
    """Small lexical retrieval, explicitly not a biomedical embedding index."""
    rows = app.state.platform_store.execute('SELECT id,title,payload FROM v5_protocols WHERE project_id=:pid ORDER BY created_at DESC', {'pid': project_id}, True)
    terms = set(re.findall(r'[a-zA-Z]{4,}', query.lower()))
    found = []
    for row in rows[:40]:
        doc = json.loads(row['payload'])
        reviews = app.state.platform_store.execute('SELECT payload FROM v5_protocol_reviews WHERE project_id=:pid AND protocol_id=:id ORDER BY created_at DESC', {'pid': project_id, 'id': row['id']}, True)
        status = json.loads(reviews[0]['payload'])['status'] if reviews else 'pending'
        if status == 'rejected':
            continue
        for e in doc['evidence']:
            score = sum(t in e['quote'].lower() for t in terms)
            if score:
                found.append((score, {'document_id': row['id'], 'title': row['title'], 'page': e['page'], 'section': e['section'], 'text': e['quote'], 'source_sha256': doc['source_sha256'], 'review_status': status}))
    found.sort(key=lambda item: item[0], reverse=True)
    return [item[1] for item in found[:5]]
