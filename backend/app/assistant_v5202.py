"""v5.2.0.2 assistant feedback routes and source-grounded context selection."""
from __future__ import annotations

import json
import re
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from .services.assistant_feedback import (
    get_reviewed_feedback_context, initialize_feedback, list_feedback, review_feedback, submit_feedback,
)
from .services.assistant_service import select_context
from .services.data_service import json_clean
from .services.cohort_graphs import present

FeedbackStatus = Literal['pending','approved','rejected']
IDENTIFIER = r'^[a-f0-9]{32}$'


class FeedbackInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    rating: int = Field(ge=1, le=5, strict=True)
    comment: str = Field(default='', max_length=4000)
    dataset_id: str | None = Field(default=None, min_length=1, max_length=200)


class FeedbackReview(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    status: FeedbackStatus
    correction: str = Field(default='', max_length=4000)


def attach_assistant_v5202(app, store, config):
    initialize_feedback(store)
    router = APIRouter(prefix='/api/v5', tags=['Assistant feedback'])

    def require_feedback_identity():
        if config.auth_mode == 'local':
            raise HTTPException(403, 'Assistant feedback requires an authenticated account. Use AUTH_MODE=session.')

    @router.post('/messages/{message_id}/feedback')
    def submit(request: Request, body: FeedbackInput, message_id: str = Path(pattern=IDENTIFIER)):
        require_feedback_identity()
        project = app.state.require_project(request, roles={'owner','researcher','reviewer'})
        user = app.state.current_user(request)
        if not store.rate_limit('assistant-feedback:' + project['id'] + ':' + user['id'], limit=60, window=60):
            raise HTTPException(429, 'Feedback request limit reached. Retry in one minute.')
        record = submit_feedback(store, project['id'], user['id'], message_id, body.rating, body.comment, body.dataset_id)
        app.state.audit(project['id'], user['id'], 'assistant.feedback', {'feedback_id':record['id'],'message_id':message_id,'rating':body.rating})
        return {'status':'recorded','feedback':record}

    @router.get('/projects/{project_id}/assistant-feedback')
    def feedback_list(request: Request, project_id: str, status: FeedbackStatus | None = None,
                      dataset_id: str | None = Query(default=None, max_length=200)):
        require_feedback_identity()
        app.state.require_project(request, project_id, roles={'owner'})
        return {'items':list_feedback(store, project_id, status, dataset_id),'limit':200}

    @router.put('/projects/{project_id}/assistant-feedback/{feedback_id}')
    def feedback_review(request: Request, project_id: str, body: FeedbackReview,
                        feedback_id: str = Path(pattern=IDENTIFIER)):
        require_feedback_identity()
        app.state.require_project(request, project_id, roles={'owner'})
        user = app.state.current_user(request)
        record = review_feedback(store, project_id, feedback_id, user['id'], body.status, body.correction)
        app.state.audit(project_id, user['id'], 'assistant.feedback.reviewed', {'feedback_id':feedback_id,'status':body.status})
        return {'feedback':record}

    app.include_router(router)


def _cohort_context(registry, dataset_id, dataset):
    frame = registry.frame(dataset_id)
    cohort = {'dataset_id':dataset_id,'row_count':len(frame),'scope':'full_dataset','is_fixture':dataset.get('is_fixture', False)}
    cohort['missingness'] = {column:sum(not present(value) for value in frame[column]) for column in
                            ('phase','status','enrollment','start_date','completion_date','brief_summary') if column in frame}
    for column in ('phase','status'):
        if column in frame:
            counts = frame[column].fillna('Unknown').astype(str).value_counts()
            cohort[column + '_counts'] = {str(key):int(count) for key,count in counts.head(20).items()}
            cohort[column + '_other_count'] = int(counts.iloc[20:].sum())
    return cohort


def _source_key(reference):
    return tuple(reference.get(key) for key in ('kind','dataset_id','nct_id','document_id','page','section','model_id','inference_id','bookmark_id','feedback_id'))


def prepare_grounded_context(app, store, project_id, dataset_id, context, references, question, nct_id=None):
    """Extend v5 preparation with authentic cohort/model/saved evidence and citations."""
    context = dict(context)
    references = [dict(ref) for ref in references]
    registry = app.state.project_registry(project_id)
    context['cohort'] = _cohort_context(registry, dataset_id, context['dataset'])
    context['reviewed_corrections'] = get_reviewed_feedback_context(store, project_id, dataset_id)
    for correction in context['reviewed_corrections']:
        references.append({'kind':'reviewed_correction','feedback_id':correction['feedback_id'],
                           'title':'Owner-reviewed project correction','reviewed_at':correction['reviewed_at']})
    model_registry = getattr(app.state, 'model_registry', None)
    models = model_registry.list_models(project_id, registry)['items'] if model_registry else []
    context['active_models'] = [{**model,'model_id':model['id']} for model in models if model.get('active')]
    for model in context['active_models']:
        references.append({'kind':'model','model_id':model['id'],'title':model['name'],
                           'artifact_sha256':model.get('artifact_sha256'),'manifest_sha256':model.get('manifest_sha256')})
    saved = store.execute('''SELECT id,payload FROM v5_inference_batches WHERE project_id=:project
        AND dataset_id=:dataset ORDER BY created_at DESC,id DESC LIMIT 5''', {'project':project_id,'dataset':dataset_id}, True) if model_registry else []
    context['saved_predictions'] = []
    for row in saved:
        result = json.loads(row['payload'])
        items = [item for item in result.get('items', []) if nct_id and item.get('nct_id') == nct_id]
        if not items:
            continue
        context['saved_predictions'].append({k:v for k,v in result.items() if k != 'items'} |
                                            {'inference_id':row['id'],'items':items[:1]})
        references.append({'kind':'saved_prediction','inference_id':row['id'],'dataset_id':dataset_id,
                           'title':'Saved inference','created_at':result.get('created_at'),'model_id':result.get('model', {}).get('id')})
    terms = set(re.findall(r'[a-zA-Z]{4,}', question.lower()))
    bookmarks = store.execute('SELECT id,payload FROM v52_bookmarks WHERE project_id=:project ORDER BY created_at DESC,id DESC LIMIT 200',
                              {'project':project_id}, True) if hasattr(app.state, 'require_verified_email') else []
    scored = []
    for row in bookmarks:
        item = json.loads(row['payload'])
        score = sum(term in (item.get('title','') + ' ' + item.get('summary','')).lower() for term in terms)
        if score:
            scored.append((score, {**item,'bookmark_id':row['id']}))
    context['saved_evidence'] = [item for _,item in sorted(scored, key=lambda pair:pair[0], reverse=True)[:5]]
    for item in context['saved_evidence']:
        references.append({'kind':'saved_evidence','bookmark_id':item['bookmark_id'],'title':item['title'],
                           'source':item['source'],'source_id':item['id'],'url':item['url'],
                           'citation':item['citation'],'retrieved_at':item['retrieved_at']})
    missing = []
    if not nct_id:
        missing.append('No study selected; cohort evidence cannot establish a particular trial outcome.')
    if not context['saved_predictions']:
        missing.append('No saved prediction for the selected study is included. Active-model metrics are cohort evaluation, not a trial prediction.')
    if not context.get('project_documents'):
        missing.append('No matching project protocol excerpt is included; full protocol contents are unavailable in this prompt.')
    if not context['saved_evidence']:
        missing.append('No matching saved external evidence is included. No live literature search was performed.')
    if context['dataset'].get('is_fixture'):
        missing.append('This dataset is a software fixture, not clinical research evidence.')
    context['missing_evidence'] = missing
    context['selected_study_text_note'] = 'Study strings and protocol quotes may be excerpts; consult the referenced source for the complete text.'
    # A stable source number refers to one exact evidence item; duplicates share
    # the same ID, including repeated excerpts from the same document page.
    unique = {}
    for reference in references:
        if isinstance(reference.get('title'), str) and len(reference['title']) > 500:
            reference = {**reference,'title':reference['title'][:500],'title_excerpt':True}
        key = _source_key(reference)
        if key not in unique:
            unique[key] = {**reference,'reference_id':'S' + str(len(unique) + 1)}
    references = list(unique.values())
    for key, kind in (('dataset','dataset'),('selected_study','study')):
        source = next((ref for ref in references if ref['kind'] == kind), None)
        if source and context.get(key):
            context[key] = {**context[key],'reference_id':source['reference_id']}
    for key, kind, identity in (('project_documents','document','document_id'),('active_models','model','model_id'),
                               ('saved_predictions','saved_prediction','inference_id'),
                               ('saved_evidence','saved_evidence','bookmark_id'),('reviewed_corrections','reviewed_correction','feedback_id')):
        for item in context.get(key, []):
            reference = next((ref for ref in references if ref['kind'] == kind and ref.get(identity) == item.get(identity)
                              and (kind != 'document' or (ref.get('page'),ref.get('section')) == (item.get('page'),item.get('section')))), None)
            if reference:
                item['reference_id'] = reference['reference_id']
    context['sources'] = references
    bounded = select_context(json_clean(context), context['profile_limits']['context_chars'])
    return bounded, bounded['sources']
