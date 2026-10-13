"""v5.2 project evidence library and opt-in account email verification."""
from __future__ import annotations

import json
import secrets
import time
import uuid
from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import text

from .platform_store import token_digest
from .research_sources import Source, SourceUnavailable, citation_url, clean_text, search
from .services.data_service import now

TOKEN_SECONDS = 3600
CACHE_SECONDS = 86400
MAIL_REASON = 'Email delivery is not configured. Set MAIL_API_KEY, MAIL_FROM and an HTTPS PUBLIC_BASE_URL on the server.'


class EmailUnavailable(Exception):
    pass


def delivery_configured(config):
    return bool(config.mail_api_key and config.mail_from and config.public_base_url)


def send_verification_email(config, email, token):
    if not delivery_configured(config):
        raise EmailUnavailable(MAIL_REASON)
    # Fragment is consumed and cleared by the UI; it is not sent in HTTP request URLs.
    link = config.public_base_url + '/#verify-email?token=' + quote(token, safe='')
    payload = {'from':config.mail_from,'to':[email], 'subject':'Verify your CTI research account',
               'text':'Confirm your email address in the CTI account screen: ' + link + '\nThis link expires in one hour. If you did not request it, ignore this email.'}
    try:
        with httpx.Client(timeout=httpx.Timeout(10, connect=5), follow_redirects=False) as client:
            # No response body is needed and no provider error content is exposed.
            with client.stream('POST','https://api.resend.com/emails',json=payload,
                               headers={'Authorization':'Bearer '+config.mail_api_key}) as response:
                if response.status_code not in {200,201,202}:
                    raise EmailUnavailable('Email delivery failed. Retry later or contact the server operator.')
    except httpx.HTTPError:
        raise EmailUnavailable('Email delivery is unavailable. Retry later or contact the server operator.') from None


class Evidence(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    source: Source
    id: str = Field(min_length=1,max_length=100)
    title: str = Field(min_length=1,max_length=500)
    summary: str = Field(default='',max_length=4000)
    url: str = Field(min_length=1,max_length=500)
    citation: str = Field(min_length=1,max_length=500)
    published_at: str | None = Field(default=None,max_length=80)
    retrieved_at: str = Field(min_length=1,max_length=80)

    @field_validator('title','summary','citation','published_at')
    @classmethod
    def plain_text(cls, value):
        return clean_text(value) if value is not None else None

    @field_validator('retrieved_at')
    @classmethod
    def timestamp(cls,value):
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            raise ValueError('Evidence retrieval time must include a timezone.')
        return value

    @model_validator(mode='after')
    def source_link(self):
        if self.url != citation_url(self.source,self.id):
            raise ValueError('The citation URL must match the evidence source and identifier.')
        if not self.title or not self.citation:
            raise ValueError('Evidence needs a title and citation.')
        return self


class VerificationToken(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    token: str = Field(min_length=16,max_length=256)


def attach_v52_routes(app):
    store = app.state.platform_store
    config = app.state.settings

    @app.exception_handler(RequestValidationError)
    async def private_token_validation(request, exc):
        if request.url.path == '/api/v5.2/auth/verify-email':
            return JSONResponse({'detail':'Provide a valid verification token.'},status_code=422)
        return await request_validation_exception_handler(request,exc)
    if config.require_email_verification and config.auth_mode == 'local':
        raise ValueError('REQUIRE_EMAIL_VERIFICATION requires AUTH_MODE=session.')
    statements = [
        'CREATE TABLE IF NOT EXISTS v52_bookmarks (id VARCHAR(64) PRIMARY KEY,project_id VARCHAR(64) NOT NULL,created_by VARCHAR(64) NOT NULL,source VARCHAR(30) NOT NULL,source_id VARCHAR(100) NOT NULL,created_at TEXT NOT NULL,payload TEXT NOT NULL,UNIQUE(project_id,source,source_id))',
        'CREATE INDEX IF NOT EXISTS v52_bookmarks_scope ON v52_bookmarks(project_id,created_at)',
        'CREATE TABLE IF NOT EXISTS v52_evidence_cache (id VARCHAR(64) PRIMARY KEY,project_id VARCHAR(64) NOT NULL,source VARCHAR(30) NOT NULL,source_id VARCHAR(100) NOT NULL,retrieved_at TEXT NOT NULL,cached_at DOUBLE PRECISION NOT NULL,expires_at DOUBLE PRECISION NOT NULL,payload TEXT NOT NULL,UNIQUE(project_id,source,source_id,retrieved_at))',
        'CREATE INDEX IF NOT EXISTS v52_evidence_cache_scope ON v52_evidence_cache(project_id,cached_at)',
        'CREATE TABLE IF NOT EXISTS v52_email_verified (user_id VARCHAR(64) PRIMARY KEY,verified_at TEXT NOT NULL)',
        'CREATE TABLE IF NOT EXISTS v52_email_tokens (token_hash VARCHAR(64) PRIMARY KEY,user_id VARCHAR(64) NOT NULL,expires_at DOUBLE PRECISION NOT NULL,created_at DOUBLE PRECISION NOT NULL)',
        'CREATE INDEX IF NOT EXISTS v52_email_tokens_user ON v52_email_tokens(user_id)',
    ]
    with store.transaction() as conn:
        for statement in statements:
            conn.execute(text(statement))

    def verified(user_id):
        return store.one('SELECT verified_at FROM v52_email_verified WHERE user_id=:user',{'user':user_id})

    def require_verified(request):
        if config.require_email_verification:
            user = app.state.current_user(request)
            if not verified(user['id']):
                raise HTTPException(403,'Verify your email address to access this workspace.')
    app.state.require_verified_email = require_verified

    router = APIRouter(prefix='/api/v5.2', tags=['Research library and account'])

    @router.get('/research/search')
    def research_search(request:Request, source:Source, q:str=Query(min_length=1,max_length=300), limit:int=Query(default=10,ge=1,le=20)):
        project = app.state.require_project(request)
        if not q.strip() or any(ord(c) < 32 for c in q):
            raise HTTPException(422,'Provide a nonempty search query without control characters.')
        user = app.state.current_user(request)
        if not store.rate_limit('v52-search:'+project['id']+':'+user['id'],limit=60,window=60):
            raise HTTPException(429,'Research search limit reached. Retry in one minute.')
        try:
            result = search(source,q.strip(),limit)
        except SourceUnavailable as exc:
            raise HTTPException(503,str(exc)) from None
        stamp = time.time()
        with store.transaction() as conn:
            conn.execute(text('UPDATE v5_projects SET name=name WHERE id=:project'),{'project':project['id']})
            conn.execute(text('DELETE FROM v52_evidence_cache WHERE project_id=:project AND expires_at<=:stamp'),{'project':project['id'],'stamp':stamp})
            for item in result['items']:
                evidence = Evidence.model_validate(item)
                conn.execute(text('INSERT INTO v52_evidence_cache(id,project_id,source,source_id,retrieved_at,cached_at,expires_at,payload) VALUES(:id,:project,:source,:source_id,:retrieved,:stamp,:expiry,:payload) ON CONFLICT(project_id,source,source_id,retrieved_at) DO UPDATE SET cached_at=excluded.cached_at,expires_at=excluded.expires_at,payload=excluded.payload'),
                    {'id':uuid.uuid4().hex,'project':project['id'],'source':evidence.source,'source_id':evidence.id,
                     'retrieved':evidence.retrieved_at,'stamp':stamp,'expiry':stamp+CACHE_SECONDS,'payload':evidence.model_dump_json()})
            conn.execute(text('DELETE FROM v52_evidence_cache WHERE id IN (SELECT id FROM v52_evidence_cache WHERE project_id=:project ORDER BY cached_at DESC,id LIMIT 100000 OFFSET 2000)'),{'project':project['id']})
        return result

    def bookmark(row):
        return {k:row[k] for k in ('id','project_id','created_by','created_at')} | {'evidence':json.loads(row['payload'])}

    @router.get('/bookmarks')
    def bookmarks(request:Request):
        project = app.state.require_project(request)
        rows = store.execute('SELECT * FROM v52_bookmarks WHERE project_id=:project ORDER BY created_at DESC,id LIMIT 200', {'project':project['id']},True)
        return {'items':[bookmark(row) for row in rows],'limit':200}

    @router.post('/bookmarks',status_code=201)
    def save_bookmark(evidence:Evidence,request:Request):
        project = app.state.require_project(request,roles={'owner','researcher'})
        user = app.state.current_user(request)
        params = {'id':uuid.uuid4().hex,'project':project['id'],'user':user['id'],'source':evidence.source,
                  'source_id':evidence.id,'created':now(),'payload':evidence.model_dump_json()}
        with store.transaction() as conn:
            # A project row lock also serializes quota checks across PostgreSQL workers.
            conn.execute(text('UPDATE v5_projects SET name=name WHERE id=:project'),params)
            existing = conn.execute(text('SELECT * FROM v52_bookmarks WHERE project_id=:project AND source=:source AND source_id=:source_id'),params).mappings().first()
            if existing:
                return bookmark(dict(existing))
            cached = conn.execute(text('SELECT payload FROM v52_evidence_cache WHERE project_id=:project AND source=:source AND source_id=:source_id AND retrieved_at=:retrieved AND expires_at>:stamp'),
                                  {**params,'retrieved':evidence.retrieved_at,'stamp':time.time()}).mappings().first()
            if not cached:
                raise HTTPException(422,'Search for this evidence in the current project before saving it. Search results expire after 24 hours.')
            # Store the canonical server result, never client-supplied source claims.
            params['payload'] = cached['payload']
            count = conn.execute(text('SELECT COUNT(*) FROM v52_bookmarks WHERE project_id=:project'),params).scalar_one()
            if count >= 200:
                raise HTTPException(429,'Project bookmark limit reached. Remove an existing bookmark.')
            conn.execute(text('INSERT INTO v52_bookmarks(id,project_id,created_by,source,source_id,created_at,payload) VALUES(:id,:project,:user,:source,:source_id,:created,:payload)'),params)
        app.state.audit(project['id'],user['id'],'evidence.saved',{'source':evidence.source,'source_id':evidence.id})
        return {'id':params['id'],'project_id':project['id'],'created_by':user['id'],'created_at':params['created'],'evidence':json.loads(params['payload'])}

    @router.delete('/bookmarks/{identifier}')
    def remove_bookmark(identifier:str,request:Request):
        project = app.state.require_project(request,roles={'owner','researcher'})
        removed = store.execute('DELETE FROM v52_bookmarks WHERE id=:id AND project_id=:project', {'id':identifier,'project':project['id']})
        if not removed:
            raise HTTPException(404,'Bookmark not found in this project.')
        app.state.audit(project['id'],app.state.current_user(request)['id'],'evidence.deleted',{'bookmark_id':identifier})
        return {'ok':True}

    @router.get('/account/verification')
    def verification_status(request:Request):
        user = app.state.current_user(request)
        row = verified(user['id'])
        session = config.auth_mode == 'session'
        configured = delivery_configured(config)
        return {'required':config.require_email_verification,'verified':bool(row),'verified_at':row['verified_at'] if row else None,
                'delivery_configured':configured,'available':session and configured,'email':user['email'] if session else None,
                'reason':('Email verification requires authenticated session mode.' if not session else MAIL_REASON if not configured else None)}

    @router.post('/account/verification/request')
    def request_verification(request:Request):
        user = app.state.current_user(request)
        if config.auth_mode != 'session':
            raise HTTPException(503,'Email verification requires authenticated session mode.')
        if verified(user['id']):
            return {'ok':True,'message':'Your email address is already verified.','expires_in_seconds':0}
        if not delivery_configured(config):
            raise HTTPException(503,MAIL_REASON)
        if not store.rate_limit('v52-mail:'+user['id'],limit=3):
            raise HTTPException(429,'Verification email limit reached. Retry in 15 minutes.')
        raw = secrets.token_urlsafe(32)
        digest = token_digest(raw)
        stamp = time.time()
        with store.transaction() as conn:
            # Stable user-before-token ordering serializes issuance across workers.
            conn.execute(text('UPDATE v5_users SET name=name WHERE id=:user'),{'user':user['id']})
            if conn.execute(text('SELECT user_id FROM v52_email_verified WHERE user_id=:user'),{'user':user['id']}).first():
                return {'ok':True,'message':'Your email address is already verified.','expires_in_seconds':0}
            conn.execute(text('DELETE FROM v52_email_tokens WHERE user_id=:user'),{'user':user['id']})
            conn.execute(text('INSERT INTO v52_email_tokens(token_hash,user_id,expires_at,created_at) VALUES(:token,:user,:expiry,:created)'),
                         {'token':digest,'user':user['id'],'expiry':stamp+TOKEN_SECONDS,'created':stamp})
        try:
            send_verification_email(config,user['email'],raw)
        except EmailUnavailable as exc:
            store.execute('DELETE FROM v52_email_tokens WHERE token_hash=:token',{'token':digest})
            raise HTTPException(503,str(exc)) from None
        return {'ok':True,'message':'Verification email sent. Check your inbox.','expires_in_seconds':TOKEN_SECONDS}

    @router.post('/auth/verify-email')
    def confirm_email(body:VerificationToken,request:Request):
        ip = request.client.host if request.client else 'unknown'
        if not store.rate_limit('v52-confirm:'+ip,limit=20):
            raise HTTPException(429,'Too many verification attempts. Retry in 15 minutes.')
        with store.transaction() as conn:
            candidate = conn.execute(text('SELECT user_id FROM v52_email_tokens WHERE token_hash=:token AND expires_at>:stamp'),
                                     {'token':token_digest(body.token),'stamp':time.time()}).mappings().first()
            if not candidate:
                raise HTTPException(400,'Verification link is invalid, expired, or already used.')
            conn.execute(text('UPDATE v5_users SET name=name WHERE id=:user'),{'user':candidate['user_id']})
            row = conn.execute(text('DELETE FROM v52_email_tokens WHERE token_hash=:token AND expires_at>:stamp RETURNING user_id'),
                               {'token':token_digest(body.token),'stamp':time.time()}).mappings().first()
            if not row:
                raise HTTPException(400,'Verification link is invalid, expired, or already used.')
            conn.execute(text('INSERT INTO v52_email_verified(user_id,verified_at) VALUES(:user,:verified) ON CONFLICT(user_id) DO NOTHING'),
                         {'user':row['user_id'],'verified':now()})
            conn.execute(text('DELETE FROM v52_email_tokens WHERE user_id=:user'),{'user':row['user_id']})
        return {'ok':True,'verified':True}

    app.include_router(router)
