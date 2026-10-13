"""v5 authentication, per-project gateway and durable contextual conversations.

Only this application is published. The v1 research factory is an internal worker,
never an alternate public bearer-token interface.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
import threading
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from typing import Literal

import pandas as pd
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from .config import Settings, settings
from .middleware.rate_limiter import RateLimiterMiddleware
from .platform_store import PlatformStore, hash_password, verify_password, token_digest
from .services import assistant_service, assistant_streaming
from .services.data_service import DatasetValidationError, SAMPLE_ID, json_clean, now
from .services.pci_service import METHODOLOGY, calculate_pci_details

Role = Literal['owner', 'researcher', 'reviewer', 'viewer']
Provider = Literal['auto', 'openai', 'anthropic', 'gemini', 'compatible']
Profile = Literal['fast', 'balanced', 'deep']
DEFAULT_SETTINGS = {'default_provider':'auto', 'default_profile':'balanced', 'chat_daily_limit':50, 'chat_retention_days':90,
                    'chat_max_output_tokens':16000,'chat_context_chars':120000}
PROFILES = {'fast':{'history_messages':6,'context_chars':16000,'max_output_tokens':2000},
            'balanced':{'history_messages':16,'context_chars':60000,'max_output_tokens':8192},
            'deep':{'history_messages':30,'context_chars':262144,'max_output_tokens':65536}}
COOKIE = 'cti_session'
WRITE_ROLES = {'owner','researcher'}
CHAT_ROLES = {'owner','researcher','reviewer'}
ROLE_LABELS = {'owner':'Owner','researcher':'Trial researcher','reviewer':'Clinical reviewer','viewer':'Viewer'}


def role_capabilities(role):
    owner = role == 'owner'
    reads = role in ROLE_LABELS
    return {'read_research':reads,'predict':reads,'explain':reads,'charts':reads,'export':reads,
            'write_research':role in WRITE_ROLES,'run_scenarios':role in WRITE_ROLES,
            'train_models':owner,'approve_models':owner,'activate_models':owner,
            'manage_members':owner,'manage_settings':owner,'chat':role in CHAT_ROLES,
            'review_protocol':role in {'owner','reviewer'},'view_audit':role in {'owner','reviewer'}}


class Input(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Credentials(Input):
    email: str = Field(min_length=3,max_length=254)
    password: str = Field(min_length=12,max_length=256)

    @field_validator('email')
    @classmethod
    def email_valid(cls,value):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):
            raise ValueError('Provide a valid email address.')
        return value.lower()


class Setup(Credentials):
    name: str = Field(min_length=1,max_length=120)
    setup_token: str = Field(max_length=256)


class PasswordChange(Input):
    current_password: str = Field(min_length=12,max_length=256)
    new_password: str = Field(min_length=12,max_length=256)


class ProjectInput(Input):
    name: str = Field(min_length=1,max_length=120)
    description: str = Field(default='',max_length=2000)


class ProjectSettings(Input):
    default_provider: Provider = 'auto'
    default_profile: Profile = 'balanced'
    chat_daily_limit: int = Field(default=50,ge=0,le=500)
    chat_retention_days: int = Field(default=90,ge=1,le=3650)
    chat_max_output_tokens: int = Field(default=16000,ge=100,le=65536)
    chat_context_chars: int = Field(default=120000,ge=2000,le=262144)


class MemberInput(Input):
    email: str = Field(min_length=3,max_length=254)
    name: str = Field(default='',max_length=120)
    role: Role

    _email = field_validator('email')(Credentials.email_valid.__func__)


class InvitationInput(Input):
    token: str = Field(min_length=16,max_length=256)
    password: str = Field(min_length=12,max_length=256)
    name: str = Field(min_length=1,max_length=120)


class ConversationInput(Input):
    title: str = Field(default='New conversation',min_length=1,max_length=120)


class MessageInput(Input):
    message: str = Field(min_length=1,max_length=4000)
    dataset_id: str = Field(default=SAMPLE_ID,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    nct_id: str | None = Field(default=None,max_length=100)
    provider: Provider | None = None
    profile: Profile | None = None


class URLInput(Input):
    url: str = Field(min_length=1,max_length=2048)
    name: str | None = Field(default=None,max_length=120)


class PasteInput(Input):
    content: str = Field(min_length=1,max_length=2_000_000)
    format: Literal['csv','json'] = 'csv'
    name: str | None = Field(default=None,max_length=120)


def _public_user(value):
    return {key:value[key] for key in ('id','email','name')} if value else None


def create_app(config: Settings | None = None):
    config = config or settings
    production = config.app_env.lower() == 'production'
    if production and config.auth_mode == 'local':
        raise ValueError('AUTH_MODE=local is forbidden in production.')
    if production:
        url = urlsplit(config.postgres_url)
        if parse_qs(url.query).get('sslmode',[''])[0] not in {'require','verify-ca','verify-full'}:
            raise ValueError('Production PostgreSQL requires sslmode=require or certificate verification.')
    store = PlatformStore(config)
    research_apps = {}
    apps_lock = threading.RLock()
    # Shared across projects: a single CPU job per process, rather than one per tenant.
    training_slot = threading.BoundedSemaphore(1)

    @asynccontextmanager
    async def lifespan(app):
        try:
            yield
        finally:
            for subapp in research_apps.values():
                if subapp.state.registry.engine is not None:
                    subapp.state.registry.engine.dispose()
            store.engine.dispose()

    app = FastAPI(title='Clinical Trial Intelligence v5.2',version='5.2.0.2',lifespan=lifespan)
    app.state.settings = config
    app.state.platform_store = store
    origins = {v.strip().rstrip('/') for v in config.cors_origins.split(',') if v.strip()}

    def current_user(request):
        if config.auth_mode == 'local':
            return {'id':'local-user','email':'local@offline.invalid','name':'Local researcher'}
        raw = request.cookies.get(COOKIE,'')
        if not raw:
            raise HTTPException(401,'Sign in to continue.')
        user = store.one('SELECT u.* FROM v5_users u JOIN v5_sessions s ON s.user_id=u.id WHERE s.token_hash=:token AND s.expires_at>:now',
                         {'token':token_digest(raw),'now':time.time()})
        if user is None:
            raise HTTPException(401,'Session expired or invalid. Sign in again.')
        return _public_user(user)

    def list_projects(user):
        rows = store.execute('SELECT p.*,m.role FROM v5_projects p JOIN v5_members m ON m.project_id=p.id WHERE m.user_id=:user ORDER BY p.created_at',{'user':user['id']},True)
        for row in rows:
            row['settings'] = {**DEFAULT_SETTINGS,**json.loads(row['settings'])}
            row['capabilities'] = role_capabilities(row['role'])
        return rows

    def require_project(request, project_id=None, roles=None):
        user = current_user(request)
        selected = request.headers.get('X-Project-ID')
        if project_id and selected and selected != project_id:
            raise HTTPException(409,'Project header does not match the requested project.')
        identifier = project_id or selected or ('local' if config.auth_mode == 'local' else None)
        if not identifier:
            raise HTTPException(400,'Select a project and send X-Project-ID.')
        row = store.one('SELECT p.*,m.role FROM v5_projects p JOIN v5_members m ON m.project_id=p.id WHERE p.id=:project AND m.user_id=:user',{'project':identifier,'user':user['id']})
        if row is None:
            raise HTTPException(403,'Project access is not permitted.')
        if row['role'] not in ROLE_LABELS:
            raise HTTPException(403,'Project role is invalid. Ask an owner to update membership.')
        if roles and row['role'] not in roles:
            raise HTTPException(403,'Your project role does not permit this action.')
        row['settings'] = {**DEFAULT_SETTINGS,**json.loads(row['settings'])}
        row['capabilities'] = role_capabilities(row['role'])
        return row

    def project_app(identifier):
        if not re.fullmatch(r'(?:[a-f0-9]{32}|local)',identifier):
            raise HTTPException(403,'Invalid project identifier.')
        with apps_lock:
            if identifier not in research_apps:
                from .main import create_research_app
                namespace = config.database_schema
                if len(namespace)>27:
                    namespace = namespace[:18]+'_'+hashlib.sha256(namespace.encode()).hexdigest()[:8]
                schema = namespace+'_p_'+identifier if namespace else 'cti_'+identifier
                local_config = config.model_copy(update={'storage_dir':str(config.store_path/'projects'/identifier),
                    'database_url':config.database_url,
                    'database_schema':schema,'api_bearer_token':'','frontend_dist':'./.no-project-frontend'})
                subapp = create_research_app(local_config, training_slot=training_slot)
                registry = subapp.state.registry
                if hasattr(app.state,'model_registry'):
                    registry.approved_model_resolver = lambda task='duration', model_name='recommended': app.state.model_registry.resolve(identifier, registry, task=task, model_id='active')
                for record in registry.list_experiments():
                    if record['status'] in {'running','queued'}:
                        record.update(status='failed',completed_at=now(),error='Server restarted before training completed. Start a new experiment to retry.')
                        registry.save_experiment(record)
                research_apps[identifier] = subapp
            return research_apps[identifier]

    app.state.current_user = current_user
    app.state.require_project = require_project
    app.state.project_registry = lambda identifier: project_app(identifier).state.registry
    app.state.research_apps = research_apps
    app.state.role_capabilities = role_capabilities

    def audit(project,user,action,details=None):
        store.execute('INSERT INTO v5_audit (id,project_id,user_id,action,details,created_at) VALUES (:id,:project,:user,:action,:details,:created)',
                      {'id':uuid.uuid4().hex,'project':project,'user':user,'action':action,'details':json.dumps(details or {}),'created':now()})
    app.state.audit = audit

    if config.auth_mode == 'local':
        with store.transaction() as conn:
            conn.execute(text('INSERT INTO v5_projects(id,name,description,settings,created_at) VALUES (:id,:name,:description,:settings,:created) ON CONFLICT(id) DO NOTHING'),
                         {'id':'local','name':'Local research workspace','description':'Explicit PostgreSQL development workspace; no identity security.', 'settings':json.dumps(DEFAULT_SETTINGS),'created':now()})
            conn.execute(text("INSERT INTO v5_members(project_id,user_id,role) VALUES ('local','local-user','owner') ON CONFLICT(project_id,user_id) DO NOTHING"))

    class ProjectGateway:
        def __init__(self, downstream):
            self.app = downstream

        async def __call__(self,scope,receive,send):
            if scope['type'] != 'http':
                return await self.app(scope,receive,send)
            received_bytes=0
            original_receive=receive
            async def bounded_receive():
                nonlocal received_bytes
                event=await original_receive()
                if event['type']=='http.request':
                    received_bytes+=len(event.get('body',b''))
                    if received_bytes>config.max_upload_bytes+65536:
                        raise HTTPException(413,'Request body exceeds the configured limit.')
                return event
            receive=bounded_receive
            original_send=send
            async def private_send(event):
                if event['type']=='http.response.start' and scope['path'].startswith('/api/'):
                    headers=[(k,v) for k,v in event.get('headers',[]) if k.lower()!=b'cache-control']
                    event={**event,'headers':headers+[(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]}
                await original_send(event)
            send=private_send
            request = Request(scope)
            path, method = scope['path'],scope['method']
            try:
                if method not in {'GET','HEAD','OPTIONS'} and path.startswith('/api/'):
                    origin = request.headers.get('origin')
                    allowed_origins = origins | ({config.public_base_url} if config.public_base_url else set())
                    if not production:
                        allowed_origins.add(str(request.base_url).rstrip('/'))
                    if origin and origin.rstrip('/') not in allowed_origins:
                        raise HTTPException(403,'Request origin is not allowed.')
                    if request.headers.get('sec-fetch-site') == 'cross-site' and not origin:
                        raise HTTPException(403,'Cross-site mutation is not allowed.')
                    raw_length = request.headers.get('content-length','0')
                    try:
                        length = int(raw_length)
                    except ValueError:
                        raise HTTPException(400,'Invalid request length.') from None
                    if length > config.max_upload_bytes + 65536:
                        raise HTTPException(413,'Request body exceeds the configured limit.')
                    # Forbid role bypass before body parsing on all v5 import writes.
                    if path.startswith('/api/v5/import/'):
                        require_project(request,roles=WRITE_ROLES)
                    if path.startswith('/api/v5/conversations'):
                        require_project(request,roles=CHAT_ROLES)
                    if path.startswith('/api/v5.2/bookmarks'):
                        require_project(request,roles=WRITE_ROLES)
                verification_exempt = path in {'/api/v1/health','/api/v5/bootstrap'} or path.startswith(('/api/v5/auth/', '/api/v5.2/auth/', '/api/v5.2/account/'))
                if path.startswith('/api/') and method != 'OPTIONS' and not verification_exempt:
                    app.state.require_verified_email(request)
                if path.startswith('/api/v1/') and path != '/api/v1/health' and method != 'OPTIONS':
                    project = require_project(request)
                    if path == '/api/v1/whatif' and project['role'] not in WRITE_ROLES:
                        raise HTTPException(403, 'Only project owners and researchers may run what-if simulations.')
                    readonly_post = path in {'/api/v1/predictions','/api/v1/phase-predictions','/api/v1/explain','/api/v1/overview/graphs'}
                    if method not in {'GET','HEAD'} and not readonly_post and project['role'] not in WRITE_ROLES:
                        raise HTTPException(403,'Your project role cannot change research data or run AI/training.')
                    if path in {'/api/v1/experiments','/api/v1/phase-experiments'} and method=='POST' and project['role']!='owner':
                        raise HTTPException(403,'Only project owners may train models.')
                    if path == '/api/v1/assistant':
                        raise HTTPException(410,'Use saved v5 conversations for quota-controlled contextual AI.')
                    subapp = project_app(project['id'])
                    async def audited_send(message):
                        if message['type']=='http.response.start' and method not in {'GET','HEAD'} and 200<=message['status']<300:
                            audit(project['id'],current_user(request)['id'],'research.'+path.removeprefix('/api/v1/'),{'method':method,'status':message['status']})
                        await send(message)
                    return await subapp(scope,receive,audited_send)
                await self.app(scope,receive,send)
            except HTTPException as exc:
                await JSONResponse({'detail':exc.detail},status_code=exc.status_code,headers=exc.headers)(scope,receive,send)

    # User middleware runs outside routing/static mounts; /api/v1 cannot fall through.
    app.add_middleware(ProjectGateway)
    app.add_middleware(RateLimiterMiddleware,default_limit=config.rate_limit_requests,
                       training_limit=config.rate_limit_training,assistant_limit=config.rate_limit_assistant,
                       trusted_proxy_hosts=config.trusted_proxy_hosts)
    app.add_middleware(CORSMiddleware,allow_origins=sorted(origins),allow_credentials=True,
                       allow_methods=['GET','POST','PUT','PATCH','DELETE'],allow_headers=['Content-Type','X-Project-ID'])


    def session_response(user,response,request):
        raw = secrets.token_urlsafe(32)
        expiry = time.time()+config.session_hours*3600
        # Rotate the browser session while preserving other signed-in devices.
        with store.transaction() as conn:
            if 'password_hash' in user:
                # A password change between verification and session creation
                # must not revive access using the previous password.
                current_hash=conn.execute(text('SELECT password_hash FROM v5_users WHERE id=:user FOR UPDATE'),{'user':user['id']}).scalar()
                if current_hash is None or not hmac.compare_digest(current_hash,user['password_hash']):
                    raise HTTPException(401,'Account credentials changed. Sign in again.')
            conn.execute(text('DELETE FROM v5_sessions WHERE expires_at<=:stamp OR token_hash=:previous'),
                         {'stamp':time.time(),'previous':token_digest(request.cookies.get(COOKIE,''))})
            conn.execute(text('INSERT INTO v5_sessions(token_hash,user_id,expires_at) VALUES(:token,:user,:expiry)'),
                         {'token':token_digest(raw),'user':user['id'],'expiry':expiry})
        response.set_cookie(COOKIE,raw,max_age=config.session_hours*3600,httponly=True,secure=production,samesite='lax',path='/')
        response.headers['Cache-Control']='no-store'
        return {'user':_public_user(user),'expires_at':datetime.fromtimestamp(expiry,timezone.utc).isoformat()}

    dummy_password_hash=hash_password('missing-account-placeholder')

    def login_limit(request, action='login'):
        ip = request.client.host if request.client else 'unknown'
        if not store.rate_limit(action+':'+ip,limit=20):
            raise HTTPException(429,'Too many authentication attempts. Try again in 15 minutes.')

    @app.get('/api/v1/health')
    def health():
        status = assistant_service.assistant_status(config)
        return {'status':'ok','version':'5.2.0.2','database':store.kind,'auth_required':config.auth_mode=='session',
                'assistant':status,'assistant_enabled':status['enabled'],'default_dataset_id':SAMPLE_ID,'sample_data':True}

    @app.get('/api/v5/bootstrap')
    def bootstrap(request:Request,response:Response):
        response.headers['Cache-Control']='no-store'
        try:
            user=current_user(request)
        except HTTPException:
            user=None
        return {'auth_required':config.auth_mode=='session','setup_required':config.auth_mode=='session' and store.one('SELECT id FROM v5_users LIMIT 1') is None,
                'user':user,'projects':list_projects(user) if user else [],'database':{'kind':store.kind,'connected':True,'offline':False},
                'capabilities':{'saved_chat':True,'project_isolation':True,'url_import':True,'auth_mode':config.auth_mode,
                    'roles':{role:{'label':ROLE_LABELS[role],**role_capabilities(role)} for role in ROLE_LABELS},
                    'assistant':assistant_service.assistant_status(config),'profiles':[{'id':key,**value} for key,value in PROFILES.items()],
                    'url_allowlist':[x.strip() for x in config.import_allowed_hosts.split(',') if x.strip()]}}

    @app.post('/api/v5/auth/setup',status_code=201)
    def setup(req:Setup,request:Request,response:Response):
        login_limit(request,'setup')
        if not config.setup_token or len(config.setup_token)<24 or not hmac.compare_digest(req.setup_token,config.setup_token):
            raise HTTPException(403,'A server-configured setup token of at least 24 characters is required.')
        identifier=uuid.uuid4().hex
        encoded=hash_password(req.password)
        with store.transaction() as conn:
            existing=conn.execute(text("INSERT INTO v5_meta(id,value) VALUES('setup','claimed') ON CONFLICT(id) DO NOTHING")).rowcount
            if not existing:
                raise HTTPException(409,'Initial setup is already complete. Sign in or use an invitation.')
            conn.execute(text('INSERT INTO v5_users(id,email,name,password_hash,created_at) VALUES(:id,:email,:name,:hash,:created)'),{'id':identifier,'email':req.email,'name':req.name,'hash':encoded,'created':now()})
        return session_response({'id':identifier,'email':req.email,'name':req.name},response,request)

    @app.post('/api/v5/auth/login')
    def login(req:Credentials,request:Request,response:Response):
        login_limit(request)
        if not store.rate_limit('login-account:'+req.email,limit=20):
            raise HTTPException(429,'Too many authentication attempts. Try again in 15 minutes.')
        user=store.one('SELECT * FROM v5_users WHERE email=:email',{'email':req.email})
        encoded=user['password_hash'] if user else dummy_password_hash
        if not verify_password(req.password,encoded) or user is None:
            raise HTTPException(401,'Email or password is incorrect.')
        return session_response(user,response,request)

    @app.post('/api/v5/auth/logout')
    def logout(request:Request,response:Response):
        store.execute('DELETE FROM v5_sessions WHERE token_hash=:token',{'token':token_digest(request.cookies.get(COOKIE,''))})
        response.delete_cookie(COOKIE,path='/',secure=production,httponly=True,samesite='lax')
        return {'ok':True}

    @app.get('/api/v5/auth/me')
    def me(request:Request):
        return {'user':current_user(request)}

    @app.post('/api/v5/auth/password')
    def change_password(req:PasswordChange,request:Request,response:Response):
        if config.auth_mode!='session':
            raise HTTPException(403,'Password changes require authenticated session mode.')
        user=current_user(request)
        login_limit(request,'password')
        row=store.one('SELECT password_hash FROM v5_users WHERE id=:user',{'user':user['id']})
        if not row or not verify_password(req.current_password,row['password_hash']):
            raise HTTPException(401,'Current password is incorrect.')
        encoded=hash_password(req.new_password)
        with store.transaction() as conn:
            # Compare-and-swap prevents concurrent changes using a stale password.
            changed=conn.execute(text('UPDATE v5_users SET password_hash=:encoded WHERE id=:user AND password_hash=:previous'),
                                 {'encoded':encoded,'user':user['id'],'previous':row['password_hash']}).rowcount
            if not changed:
                raise HTTPException(409,'Password changed in another session. Sign in again.')
            conn.execute(text('DELETE FROM v5_sessions WHERE user_id=:user'),{'user':user['id']})
        return session_response(user,response,request)

    @app.post('/api/v5/auth/logout-all')
    def logout_all(request:Request,response:Response):
        user=current_user(request)
        store.execute('DELETE FROM v5_sessions WHERE user_id=:user',{'user':user['id']})
        response.delete_cookie(COOKIE,path='/',secure=production,httponly=True,samesite='lax')
        return {'ok':True}

    @app.get('/api/v5/projects')
    def projects(request:Request):
        return {'items':list_projects(current_user(request))}

    @app.post('/api/v5/projects',status_code=201)
    def create_project(req:ProjectInput,request:Request):
        user=current_user(request)
        if config.auth_mode=='local':
            raise HTTPException(403,'Local mode has one explicit workspace. Enable sessions to create projects.')
        identifier=uuid.uuid4().hex
        created=now()
        with store.transaction() as conn:
            conn.execute(text('SELECT id FROM v5_users WHERE id=:user FOR UPDATE'),{'user':user['id']})
            count=conn.execute(text('SELECT COUNT(*) FROM v5_members WHERE user_id=:user'),{'user':user['id']}).scalar_one()
            if count>=config.max_projects_per_user:
                raise HTTPException(429,'Project limit reached.')
            conn.execute(text('INSERT INTO v5_projects(id,name,description,settings,created_at) VALUES(:id,:name,:description,:settings,:created)'),{'id':identifier,'name':req.name,'description':req.description,'settings':json.dumps(DEFAULT_SETTINGS),'created':created})
            conn.execute(text("INSERT INTO v5_members(project_id,user_id,role) VALUES(:project,:user,'owner')"),{'project':identifier,'user':user['id']})
        audit(identifier,user['id'],'project.created')
        return {'id':identifier,'name':req.name,'description':req.description,'settings':DEFAULT_SETTINGS.copy(),'role':'owner',
                'capabilities':role_capabilities('owner'),'created_at':created}

    @app.get('/api/v5/projects/{project_id}/settings')
    def get_settings(project_id:str,request:Request):
        return require_project(request,project_id)['settings']

    @app.put('/api/v5/projects/{project_id}/settings')
    def update_settings(project_id:str,req:ProjectSettings,request:Request):
        project=require_project(request,project_id,{'owner'})
        value={**project['settings'],**req.model_dump(exclude_unset=True)}
        store.execute('UPDATE v5_projects SET settings=:settings WHERE id=:id',{'settings':json.dumps(value),'id':project_id})
        audit(project_id,current_user(request)['id'],'settings.updated',{'fields':list(req.model_fields_set)})
        return value

    @app.get('/api/v5/projects/{project_id}/members')
    def members(project_id:str,request:Request):
        require_project(request,project_id)
        if config.auth_mode=='local':
            return {'items':[{'user_id':'local-user','email':'local@offline.invalid','name':'Local researcher','role':'owner'}]}
        return {'items':store.execute('SELECT u.id AS user_id,u.email,u.name,m.role FROM v5_members m JOIN v5_users u ON u.id=m.user_id WHERE m.project_id=:project',{'project':project_id},True)}

    @app.post('/api/v5/projects/{project_id}/members',status_code=201)
    def add_member(project_id:str,req:MemberInput,request:Request):
        require_project(request,project_id,{'owner'})
        if config.auth_mode=='local':
            raise HTTPException(403,'Members require authenticated session mode.')
        user=store.one('SELECT * FROM v5_users WHERE email=:email',{'email':req.email})
        if user:
            with store.transaction() as conn:
                # Serialize membership changes across workers before checking
                # the final-owner invariant.
                conn.execute(text('SELECT id FROM v5_projects WHERE id=:project FOR UPDATE'),{'project':project_id})
                old=conn.execute(text('SELECT role FROM v5_members WHERE project_id=:project AND user_id=:user'),{'project':project_id,'user':user['id']}).scalar()
                if old=='owner' and req.role!='owner':
                    count=conn.execute(text("SELECT COUNT(*) FROM v5_members WHERE project_id=:project AND role='owner'"),{'project':project_id}).scalar_one()
                    if count<=1:
                        raise HTTPException(409,'Keep at least one project owner.')
                conn.execute(text('INSERT INTO v5_members(project_id,user_id,role) VALUES(:project,:user,:role) ON CONFLICT(project_id,user_id) DO UPDATE SET role=excluded.role'),{'project':project_id,'user':user['id'],'role':req.role})
            result={'user_id':user['id'],'email':req.email,'name':user['name'],'role':req.role}
        else:
            token=secrets.token_urlsafe(32)
            store.execute('INSERT INTO v5_invitations(token_hash,project_id,email,name,role,expires_at) VALUES(:token,:project,:email,:name,:role,:expiry)',{'token':token_digest(token),'project':project_id,'email':req.email,'name':req.name,'role':req.role,'expiry':time.time()+86400})
            result={'user_id':None,'email':req.email,'name':req.name,'role':req.role,'invitation_token':token,'expires_in_seconds':86400}
        audit(project_id,current_user(request)['id'],'member.added',{'email':req.email,'role':req.role})
        return result

    @app.post('/api/v5/auth/accept-invite')
    def accept_invite(req:InvitationInput,request:Request,response:Response):
        login_limit(request,'invite')
        hashed=token_digest(req.token)
        with store.transaction() as conn:
            row=conn.execute(text('DELETE FROM v5_invitations WHERE token_hash=:token AND expires_at>:stamp RETURNING project_id,email,name,role'),{'token':hashed,'stamp':time.time()}).mappings().first()
            if row is None:
                raise HTTPException(404,'Invitation is invalid, expired, or already used.')
            if conn.execute(text('SELECT id FROM v5_users WHERE email=:email'),{'email':row['email']}).first():
                raise HTTPException(409,'Account already exists. Ask the owner to add your existing account.')
            user={'id':uuid.uuid4().hex,'email':row['email'],'name':req.name}
            conn.execute(text('INSERT INTO v5_users(id,email,name,password_hash,created_at) VALUES(:id,:email,:name,:hash,:created)'),{**user,'hash':hash_password(req.password),'created':now()})
            conn.execute(text('INSERT INTO v5_members(project_id,user_id,role) VALUES(:project,:user,:role)'),{'project':row['project_id'],'user':user['id'],'role':row['role']})
        audit(row['project_id'],user['id'],'invitation.accepted')
        return session_response(user,response,request)

    @app.delete('/api/v5/projects/{project_id}/members/{user_id}')
    def remove_member(project_id:str,user_id:str,request:Request):
        require_project(request,project_id,{'owner'})
        if config.auth_mode!='session':
            raise HTTPException(403,'Membership changes require authenticated session mode.')
        actor=current_user(request)
        with store.transaction() as conn:
            conn.execute(text('SELECT id FROM v5_projects WHERE id=:project FOR UPDATE'),{'project':project_id})
            role=conn.execute(text('SELECT role FROM v5_members WHERE project_id=:project AND user_id=:user'),{'project':project_id,'user':user_id}).scalar()
            if role is None:
                raise HTTPException(404,'Project member not found.')
            if role=='owner':
                owners=conn.execute(text("SELECT COUNT(*) FROM v5_members WHERE project_id=:project AND role='owner'"),{'project':project_id}).scalar_one()
                if owners<=1:
                    raise HTTPException(409,'Keep at least one project owner.')
            conn.execute(text('DELETE FROM v5_members WHERE project_id=:project AND user_id=:user'),{'project':project_id,'user':user_id})
        audit(project_id,actor['id'],'member.removed',{'user_id':user_id})
        return {'ok':True}

    @app.get('/api/v5/projects/{project_id}/audit')
    def audit_events(project_id:str,request:Request):
        require_project(request,project_id,{'owner','reviewer'})
        rows=store.execute('SELECT * FROM v5_audit WHERE project_id=:project ORDER BY created_at DESC LIMIT 200',{'project':project_id},True)
        for row in rows:row['details']=json.loads(row['details'])
        return {'items':rows,'limit':200,'integrity':'Application audit history; not externally immutable or an electronic signature.'}

    @app.get('/api/v5/projects/{project_id}/usage')
    def usage(project_id:str,request:Request):
        project=require_project(request,project_id)
        day=datetime.now(timezone.utc).date().isoformat()
        row=store.one('SELECT chat_requests FROM v5_usage WHERE project_id=:project AND day=:day',{'project':project_id,'day':day})
        return {'day':day,'chat_requests_today':row['chat_requests'] if row else 0,'chat_daily_limit':project['settings']['chat_daily_limit'],
                'scope':'project','unit':'provider requests (not token charges)','retention_days':project['settings']['chat_retention_days']}

    def expire_chats(project):
        cutoff=(datetime.now(timezone.utc)-timedelta(days=project['settings']['chat_retention_days'])).isoformat()
        with store.transaction() as conn:
            conn.execute(text('DELETE FROM v5_messages WHERE conversation_id IN (SELECT id FROM v5_conversations WHERE project_id=:project AND updated_at<:cutoff AND busy_until<:stamp)'),{'project':project['id'],'cutoff':cutoff,'stamp':time.time()})
            conn.execute(text('DELETE FROM v5_conversations WHERE project_id=:project AND updated_at<:cutoff AND busy_until<:stamp'),{'project':project['id'],'cutoff':cutoff,'stamp':time.time()})

    def conversation_for(identifier,request):
        project=require_project(request)
        expire_chats(project)
        user=current_user(request)
        row=store.one('SELECT * FROM v5_conversations WHERE id=:id AND project_id=:project AND user_id=:user',{'id':identifier,'project':project['id'],'user':user['id']})
        if row is None:
            raise HTTPException(404,'Conversation not found.')
        row.pop('busy_until',None)
        return row,project,user

    def messages_for(identifier):
        rows=store.execute('SELECT * FROM v5_messages WHERE conversation_id=:id ORDER BY created_at,id',{'id':identifier},True)
        return [{**{k:v for k,v in row.items() if k not in {'metadata','conversation_id'}},**json.loads(row['metadata'])} for row in rows]

    def save_message(identifier,role,content,status,metadata=None):
        row={'id':uuid.uuid4().hex,'conversation':identifier,'role':role,'content':content,'status':status,'created':now(),'metadata':json.dumps(metadata or {})}
        store.execute('INSERT INTO v5_messages(id,conversation_id,role,content,status,created_at,metadata) VALUES(:id,:conversation,:role,:content,:status,:created,:metadata)',row)
        store.execute('UPDATE v5_conversations SET updated_at=:created WHERE id=:id',{'created':row['created'],'id':identifier})
        return row['id']

    @app.get('/api/v5/conversations')
    def conversations(request:Request):
        project=require_project(request)
        expire_chats(project)
        return {'items':store.execute('SELECT id,title,created_at,updated_at FROM v5_conversations WHERE project_id=:project AND user_id=:user ORDER BY updated_at DESC',{'project':project['id'],'user':current_user(request)['id']},True)}

    @app.post('/api/v5/conversations',status_code=201)
    def new_conversation(req:ConversationInput,request:Request):
        project=require_project(request)
        user=current_user(request)
        expire_chats(project)
        row={'id':uuid.uuid4().hex,'title':req.title,'created_at':now(),'updated_at':now()}
        with store.transaction() as conn:
            conn.execute(text('SELECT id FROM v5_users WHERE id=:user FOR UPDATE'),{'user':user['id']})
            count=conn.execute(text('SELECT COUNT(*) FROM v5_conversations WHERE project_id=:project AND user_id=:user'),{'project':project['id'],'user':user['id']}).scalar_one()
            if count>=config.max_conversations_per_user:
                raise HTTPException(429,'Conversation limit reached. Delete an old conversation.')
            conn.execute(text('INSERT INTO v5_conversations(id,project_id,user_id,title,created_at,updated_at) VALUES(:id,:project,:user,:title,:created_at,:updated_at)'),{**row,'project':project['id'],'user':user['id']})
        audit(project['id'],user['id'],'conversation.created',{'conversation_id':row['id']})
        return row

    @app.get('/api/v5/conversations/{identifier}')
    def conversation(identifier:str,request:Request):
        row,_,_=conversation_for(identifier,request)
        return {**row,'messages':messages_for(identifier)}

    @app.patch('/api/v5/conversations/{identifier}')
    def rename_conversation(identifier:str,req:ConversationInput,request:Request):
        row,project,user=conversation_for(identifier,request)
        store.execute('UPDATE v5_conversations SET title=:title,updated_at=:stamp WHERE id=:id',{'title':req.title,'stamp':now(),'id':identifier})
        audit(project['id'],user['id'],'conversation.renamed',{'conversation_id':identifier})
        return {**row,'title':req.title}

    @app.delete('/api/v5/conversations/{identifier}')
    def delete_conversation(identifier:str,request:Request):
        _,project,user=conversation_for(identifier,request)
        with store.transaction() as conn:
            changed=conn.execute(text('DELETE FROM v5_conversations WHERE id=:id AND busy_until<:stamp'),{'id':identifier,'stamp':time.time()}).rowcount
            if not changed:
                raise HTTPException(409,'A reply is in progress. Retry after it completes.')
            conn.execute(text('DELETE FROM v5_messages WHERE conversation_id=:id'),{'id':identifier})
        audit(project['id'],user['id'],'conversation.deleted',{'conversation_id':identifier})
        return {'ok':True}

    def prepare_message(identifier,req,request,streaming=False):
        row,project,user=conversation_for(identifier,request)
        if project['role'] not in CHAT_ROLES:
            raise HTTPException(403,'Your project role cannot invoke paid AI providers.')
        selected_provider=None
        profile=req.profile or project['settings']['default_profile']
        limits=assistant_service.resolve_profile_limits(config,project['settings'],PROFILES[profile])
        registry=app.state.project_registry(project['id'])
        data=registry.get_dataset(req.dataset_id)
        if data is None:raise HTTPException(404,'Dataset not found in this project.')
        history=messages_for(identifier)
        if len(history)+2>config.max_messages_per_conversation:
            raise HTTPException(429,'Conversation message limit reached. Start another conversation.')
        references=[{'kind':'dataset','dataset_id':data['id'],'title':data['name'],'source':data['source'],'source_sha256':data['sha256'],'is_fixture':data['is_fixture']}]
        history_budget = limits['context_chars'] // 3
        history_limit = max(100, history_budget // max(1,min(len(history),limits['history_messages'])))
        context={'dataset':{k:data[k] for k in ('id','name','source','row_count','sha256','is_fixture')},'pci_methodology':METHODOLOGY,
                 'history':[{'role':m['role'],'content':m['content'][:history_limit],'status':m['status']} for m in history[-limits['history_messages']:]],
                 'profile':profile,'profile_limits':limits}
        if req.nct_id:
            frame=registry.frame(req.dataset_id)
            selected=frame[frame.nct_id.astype(str)==req.nct_id]
            if selected.empty:raise HTTPException(404,'Study not found in this dataset.')
            study=json_clean(selected.iloc[0].to_dict())
            context['selected_study']={k:(v[:1500] if isinstance(v,str) else v) for k,v in study.items()}
            context['pci']=calculate_pci_details(study)
            references.append({'kind':'study','dataset_id':data['id'],'nct_id':req.nct_id,'title':study['title'],'source_sha256':data['sha256']})
        try:
            from .v5_protocol import retrieve_project_evidence
            documents=retrieve_project_evidence(app,project['id'],req.message)
            documents=[{**item,'text':item.get('text','')[:1000]} for item in documents[:5]]
            context['project_documents']=documents
            references.extend([{'kind':'document',**{k:v for k,v in item.items() if k!='text'}} for item in documents])
        except ImportError:
            pass
        from .assistant_v5202 import prepare_grounded_context
        context,references=prepare_grounded_context(app,store,project['id'],req.dataset_id,context,references,req.message,req.nct_id)
        if streaming:
            try:
                selected_provider=assistant_streaming.select_provider(config,req.provider or project['settings']['default_provider'])
            except assistant_service.AssistantUnavailable as exc:
                raise HTTPException(503,str(exc)) from None
        day=datetime.now(timezone.utc).date().isoformat()
        message_id=uuid.uuid4().hex
        created=now()
        with store.transaction() as conn:
            locked=conn.execute(text('UPDATE v5_conversations SET busy_until=:until WHERE id=:id AND busy_until<:stamp'),{'id':identifier,'until':time.time()+180,'stamp':time.time()}).rowcount
            if not locked:raise HTTPException(409,'A reply is already in progress in this conversation.')
            message_count=conn.execute(text('SELECT COUNT(*) FROM v5_messages WHERE conversation_id=:id'),{'id':identifier}).scalar_one()
            if message_count+2>config.max_messages_per_conversation:
                raise HTTPException(429,'Conversation message limit reached. Start another conversation.')
            conn.execute(text('INSERT INTO v5_usage(project_id,day,chat_requests) VALUES(:project,:day,0) ON CONFLICT(project_id,day) DO NOTHING'),{'project':project['id'],'day':day})
            reserved=conn.execute(text('UPDATE v5_usage SET chat_requests=chat_requests+1 WHERE project_id=:project AND day=:day AND (:limit=0 OR chat_requests<:limit)'),{'project':project['id'],'day':day,'limit':project['settings']['chat_daily_limit']}).rowcount
            if not reserved:raise HTTPException(429,'Project daily AI request quota reached.')
            conn.execute(text("INSERT INTO v5_messages(id,conversation_id,role,content,status,created_at,metadata) VALUES(:id,:conversation,'user',:content,'pending',:created,:metadata)"),
                         {'id':message_id,'conversation':identifier,'content':req.message,'created':created,'metadata':json.dumps({'profile':profile,'references':references})})
            conn.execute(text('UPDATE v5_conversations SET updated_at=:created WHERE id=:id'),{'id':identifier,'created':created})
        return {'project':project,'user':user,'profile':profile,'limits':limits,'context':context,
                'references':references,'day':day,'message_id':message_id,'selected':selected_provider}

    @app.post('/api/v5/conversations/{identifier}/messages')
    def send_message(identifier:str,req:MessageInput,request:Request):
        prepared=prepare_message(identifier,req,request)
        project,user,profile,limits,context,references,day,message_id=(prepared[key] for key in ('project','user','profile','limits','context','references','day','message_id'))
        try:
            result=assistant_service.assist(config,req.message,context,req.provider or project['settings']['default_provider'])
            if not isinstance(result,dict) or not isinstance(result.get('reply'),str) or not result['reply'].strip():
                raise assistant_service.AssistantUnavailable('Provider returned an invalid response. Retry or inspect server settings.')
            if len(result['reply'])>assistant_service.reply_char_limit(context):
                raise assistant_service.AssistantUnavailable('Provider reply exceeded the output limit. No partial reply was saved.')
            result={**result,'profile':profile,'profile_limits':limits,'references':references}
            store.execute("UPDATE v5_messages SET status='complete' WHERE id=:id",{'id':message_id})
            save_message(identifier,'assistant',result['reply'],'complete',{k:v for k,v in result.items() if k!='reply'})
            audit(project['id'],user['id'],'chat.completed',{'conversation_id':identifier,'provider':result.get('provider_id'),'model':result.get('model'),'profile':profile})
            return {**result,'conversation_id':identifier,'messages':messages_for(identifier)}
        except assistant_service.AssistantUnavailable as exc:
            store.execute("UPDATE v5_messages SET status='failed',metadata=:metadata WHERE id=:id",{'id':message_id,'metadata':json.dumps({'error':str(exc),'profile':profile,'references':references})})
            if not assistant_service.provider_candidates(config,req.provider or project['settings']['default_provider']):
                store.execute('UPDATE v5_usage SET chat_requests=chat_requests-1 WHERE project_id=:project AND day=:day AND chat_requests>0',{'project':project['id'],'day':day})
            audit(project['id'],user['id'],'chat.failed',{'conversation_id':identifier,'profile':profile})
            raise HTTPException(503,str(exc)) from None
        finally:
            store.execute('UPDATE v5_conversations SET busy_until=0 WHERE id=:id',{'id':identifier})

    @app.post('/api/v5/conversations/{identifier}/messages/stream')
    def stream_message(identifier:str,req:MessageInput,request:Request):
        prepared=prepare_message(identifier,req,request,streaming=True)
        project,user,profile,limits,context,references,message_id,selected=(prepared[key] for key in ('project','user','profile','limits','context','references','message_id','selected'))
        state={'complete':False,'error':'Reply interrupted. No partial assistant reply was saved.','cleaned':False}

        def cleanup():
            if state['cleaned']:
                return
            state['cleaned']=True
            try:
                if not state['complete']:
                    store.execute("UPDATE v5_messages SET status='failed',metadata=:metadata WHERE id=:id AND status='pending'",
                                  {'id':message_id,'metadata':json.dumps({'error':state['error'],'profile':profile,'references':references})})
                    audit(project['id'],user['id'],'chat.failed',{'conversation_id':identifier,'profile':profile})
            finally:
                store.execute('UPDATE v5_conversations SET busy_until=0 WHERE id=:id',{'id':identifier})

        def persist_result(result):
            result={**result,'profile':profile,'profile_limits':limits,'references':references}
            created=now()
            # User status, assistant reply and audit commit together. A failed
            # insert leaves the user pending so cleanup can mark it failed.
            with store.transaction() as conn:
                conn.execute(text("UPDATE v5_messages SET status='complete' WHERE id=:id"),{'id':message_id})
                conn.execute(text("INSERT INTO v5_messages(id,conversation_id,role,content,status,created_at,metadata) VALUES(:id,:conversation,'assistant',:content,'complete',:created,:metadata)"),
                             {'id':uuid.uuid4().hex,'conversation':identifier,'content':result['reply'],'created':created,
                              'metadata':json.dumps({k:v for k,v in result.items() if k!='reply'})})
                conn.execute(text('UPDATE v5_conversations SET updated_at=:created WHERE id=:id'),{'id':identifier,'created':created})
                conn.execute(text('INSERT INTO v5_audit (id,project_id,user_id,action,details,created_at) VALUES (:id,:project,:user,:action,:details,:created)'),
                             {'id':uuid.uuid4().hex,'project':project['id'],'user':user['id'],'action':'chat.completed',
                              'details':json.dumps({'conversation_id':identifier,'provider':selected,'model':result['model'],'profile':profile}),'created':created})
                rows=conn.execute(text('SELECT * FROM v5_messages WHERE conversation_id=:id ORDER BY created_at,id'),{'id':identifier}).mappings().all()
                messages=[{**{k:v for k,v in row.items() if k not in {'metadata','conversation_id'}},**json.loads(row['metadata'])} for row in rows]
            state['complete']=True
            return {**result,'conversation_id':identifier,'messages':messages}

        async def body():
            upstream=assistant_streaming.stream_assist(config,req.message,context,selected)
            try:
                yield assistant_streaming.sse('meta',{'provider':assistant_service.PROVIDERS[selected],
                    'model':assistant_service._model(config,selected),'references':references,
                    'output_char_limit':assistant_service.reply_char_limit(context)})
                async for item in upstream:
                    if item['event']=='delta':
                        yield assistant_streaming.sse('delta',{'text':item['text']})
                    elif item['event']=='done':
                        yield assistant_streaming.sse('done',persist_result(item['result']))
            except assistant_service.AssistantUnavailable as exc:
                state['error']=str(exc)
                cleanup()
                yield assistant_streaming.sse('error',{'message':state['error']})
            except Exception:
                state['error']='Reply could not be completed or saved. Retry the request.'
                cleanup()
                yield assistant_streaming.sse('error',{'message':state['error']})
            finally:
                await upstream.aclose()
                cleanup()

        return assistant_streaming.ReplyStreamingResponse(body(),cleanup)

    def register_import(project,user,raw,filename,name,source,provenance,canonical=None):
        try:
            result=app.state.project_registry(project['id']).register_bytes(raw,filename,name=name,source=source,provenance=provenance,canonical_frame=canonical)
        except DatasetValidationError as exc:
            raise HTTPException(422,{'message':str(exc),'errors':exc.errors}) from None
        audit(project['id'],user['id'],'dataset.imported',{'dataset_id':result['id'],'source':source,'sha256':result['sha256']})
        return result

    @app.post('/api/v5/import/paste',status_code=201)
    def paste(req:PasteInput,request:Request):
        project=require_project(request,roles=WRITE_ROLES)
        raw=req.content.encode('utf-8')
        if len(raw)>min(config.max_upload_bytes,2_000_000):raise HTTPException(413,'Pasted data exceeds the limit.')
        canonical=None
        if req.format=='json':
            try:
                from .services.tabular_import import json_frame
                canonical=json_frame(req.content)
            except (ValueError,TypeError):raise HTTPException(422,'JSON must be a nonempty array of flat study records.') from None
        return register_import(project,current_user(request),raw,'pasted.'+req.format,req.name,'user pasted data',{'method':'paste'},canonical)

    @app.post('/api/v5/import/url',status_code=201)
    def url_import(req:URLInput,request:Request):
        from .services.safe_import import fetch_import
        project=require_project(request,roles=WRITE_ROLES)
        raw,filename,canonical=fetch_import(req.url,config)
        return register_import(project,current_user(request),raw,filename,req.name,'HTTPS URL import',{'method':'url','url':req.url},canonical)

    try:
        from .v5_protocol import attach_protocol_routes
    except ImportError:
        attach_protocol_routes=None
    if attach_protocol_routes:
        attach_protocol_routes(app)
    try:
        from .v5_inference import attach_inference_routes
    except ImportError:
        attach_inference_routes=None
    if attach_inference_routes:
        attach_inference_routes(app)
    from .v52 import attach_v52_routes
    attach_v52_routes(app)
    from .assistant_v5202 import attach_assistant_v5202
    attach_assistant_v5202(app,store,config)
    dist=config.path(config.frontend_dist)
    if dist.is_dir() and (dist/'index.html').is_file():
        app.mount('/',StaticFiles(directory=dist,html=True),name='frontend')
    return app
