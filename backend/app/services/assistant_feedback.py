"""Authenticated, project-scoped feedback and explicitly reviewed prompt corrections.

Feedback is metadata in PostgreSQL. It is never a filesystem path, a training
example applied automatically, or permission to change an approved model.
"""
from __future__ import annotations

import json
import uuid

from fastapi import HTTPException
from sqlalchemy import text

from .data_service import now


def initialize_feedback(store):
    if store.kind != 'postgresql':
        raise ValueError('Assistant feedback requires PostgreSQL.')
    statements = [
        '''CREATE TABLE IF NOT EXISTS v5202_assistant_feedback (
            id VARCHAR(64) PRIMARY KEY,
            project_id VARCHAR(64) NOT NULL REFERENCES v5_projects(id) ON DELETE CASCADE,
            user_id VARCHAR(64) NOT NULL REFERENCES v5_users(id) ON DELETE CASCADE,
            conversation_id VARCHAR(64) NOT NULL REFERENCES v5_conversations(id) ON DELETE CASCADE,
            message_id VARCHAR(64) NOT NULL REFERENCES v5_messages(id) ON DELETE CASCADE,
            dataset_id VARCHAR(200), rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            comment TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            review_status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK(review_status IN ('pending','approved','rejected')),
            correction TEXT NOT NULL DEFAULT '', reviewed_by VARCHAR(64), reviewed_at TEXT,
            UNIQUE(project_id,user_id,message_id)
        )''',
        'CREATE INDEX IF NOT EXISTS v5202_feedback_scope ON v5202_assistant_feedback(project_id,review_status,dataset_id,updated_at)',
    ]
    with store.transaction() as conn:
        for statement in statements:
            conn.execute(text(statement))


def submit_feedback(store, project_id, user_id, message_id, rating, comment='', dataset_id=None):
    """Resolve ownership from stored messages, never from client-supplied claims."""
    with store.transaction() as conn:
        row = conn.execute(text('''SELECT m.*,c.project_id,c.user_id FROM v5_messages m
            JOIN v5_conversations c ON c.id=m.conversation_id
            WHERE m.id=:message AND c.project_id=:project AND c.user_id=:user
            AND m.role='assistant' AND m.status='complete' FOR SHARE OF m,c'''),
            {'message':message_id,'project':project_id,'user':user_id}).mappings().first()
        if not row:
            raise HTTPException(404, 'Completed assistant message not found in your project conversation.')
        metadata = json.loads(row['metadata'])
        datasets = {ref.get('dataset_id') for ref in metadata.get('references', []) if ref.get('dataset_id')}
        if dataset_id is not None and dataset_id not in datasets:
            raise HTTPException(422, 'The dataset must be one of the message source datasets.')
        if dataset_id is None and len(datasets) == 1:
            dataset_id = next(iter(datasets))
        stamp = now()
        params = {'id':uuid.uuid4().hex,'project':project_id,'user':user_id,'conversation':row['conversation_id'],
                  'message':message_id,'dataset':dataset_id,'rating':rating,'comment':comment.strip(),'stamp':stamp}
        conn.execute(text('''INSERT INTO v5202_assistant_feedback
            (id,project_id,user_id,conversation_id,message_id,dataset_id,rating,comment,created_at,updated_at)
            VALUES(:id,:project,:user,:conversation,:message,:dataset,:rating,:comment,:stamp,:stamp)
            ON CONFLICT(project_id,user_id,message_id) DO UPDATE SET
            dataset_id=EXCLUDED.dataset_id,rating=EXCLUDED.rating,comment=EXCLUDED.comment,updated_at=EXCLUDED.updated_at,
            review_status='pending',correction='',reviewed_by=NULL,reviewed_at=NULL'''), params)
        return dict(conn.execute(text('''SELECT * FROM v5202_assistant_feedback
            WHERE project_id=:project AND user_id=:user AND message_id=:message'''), params).mappings().one())


def list_feedback(store, project_id, status=None, dataset_id=None):
    params = {'project':project_id,'status':status,'dataset':dataset_id}
    rows = store.execute('''SELECT f.*,m.content AS assistant_reply,m.metadata AS source_metadata,
        (SELECT q.content FROM v5_messages q WHERE q.conversation_id=f.conversation_id
         AND q.role='user' AND q.status='complete' AND q.created_at<=m.created_at
         ORDER BY q.created_at DESC,q.id DESC LIMIT 1) AS question
        FROM v5202_assistant_feedback f JOIN v5_messages m ON m.id=f.message_id
        JOIN v5_conversations c ON c.id=f.conversation_id AND c.project_id=f.project_id AND c.user_id=f.user_id
        WHERE f.project_id=:project AND m.status='complete' AND m.role='assistant'
        AND (CAST(:status AS TEXT) IS NULL OR f.review_status=:status)
        AND (CAST(:dataset AS TEXT) IS NULL OR f.dataset_id=:dataset)
        ORDER BY f.updated_at DESC,f.id DESC LIMIT 200''', params, True)
    for row in rows:
        row['source_references'] = json.loads(row.pop('source_metadata')).get('references', [])
    return rows


def review_feedback(store, project_id, feedback_id, reviewer_id, status, correction):
    correction = correction.strip()
    if status == 'approved' and not correction:
        raise HTTPException(422, 'An approved review needs an explicit correction or guidance.')
    with store.transaction() as conn:
        rows = conn.execute(text('''UPDATE v5202_assistant_feedback SET
            review_status=:status,correction=:correction,reviewed_by=:reviewer,reviewed_at=:stamp,updated_at=:stamp
            WHERE id=:id AND project_id=:project RETURNING *'''),
            {'id':feedback_id,'project':project_id,'reviewer':reviewer_id,'status':status,'correction':correction,'stamp':now()}).mappings().all()
        if not rows:
            raise HTTPException(404, 'Feedback not found in this project.')
        return dict(rows[0])


def get_reviewed_feedback_context(store, project_id, dataset_id=None):
    """Only explicit owner-approved corrections for this project's answer scope."""
    rows = store.execute('''SELECT f.id,f.message_id,f.dataset_id,f.correction,f.reviewed_at,m.metadata
        FROM v5202_assistant_feedback f
        JOIN v5_messages m ON m.id=f.message_id AND m.conversation_id=f.conversation_id
        JOIN v5_conversations c ON c.id=f.conversation_id AND c.project_id=f.project_id AND c.user_id=f.user_id
        WHERE f.project_id=:project AND f.review_status='approved' AND f.correction<>''
        AND m.role='assistant' AND m.status='complete'
        AND (f.dataset_id IS NULL OR f.dataset_id=CAST(:dataset AS TEXT))
        ORDER BY f.reviewed_at DESC,f.id DESC LIMIT 12''', {'project':project_id,'dataset':dataset_id}, True)
    return [{'feedback_id':row['id'],'message_id':row['message_id'],'dataset_id':row['dataset_id'],
             'correction':row['correction'],'reviewed_at':row['reviewed_at'],
             'review_scope':'owner-reviewed project guidance; model weights unchanged',
             'original_source_references':json.loads(row['metadata']).get('references', [])} for row in rows]
