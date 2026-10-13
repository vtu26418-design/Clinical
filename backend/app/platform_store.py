"""Transactional platform metadata stored exclusively in private PostgreSQL schemas."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import re
import threading
import time
from contextlib import contextmanager

from sqlalchemy import create_engine, text

SCHEMA = [
    'CREATE TABLE IF NOT EXISTS v5_users (id VARCHAR(64) PRIMARY KEY,email VARCHAR(254) UNIQUE NOT NULL,name TEXT NOT NULL,password_hash TEXT NOT NULL,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_meta (id VARCHAR(80) PRIMARY KEY,value TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_sessions (token_hash VARCHAR(64) PRIMARY KEY,user_id VARCHAR(64) NOT NULL,expires_at DOUBLE PRECISION NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_projects (id VARCHAR(64) PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,settings TEXT NOT NULL,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_members (project_id VARCHAR(64) NOT NULL,user_id VARCHAR(64) NOT NULL,role VARCHAR(20) NOT NULL,PRIMARY KEY(project_id,user_id))',
    'CREATE TABLE IF NOT EXISTS v5_invitations (token_hash VARCHAR(64) PRIMARY KEY,project_id VARCHAR(64) NOT NULL,email TEXT NOT NULL,name TEXT NOT NULL,role VARCHAR(20) NOT NULL,expires_at DOUBLE PRECISION NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_audit (id VARCHAR(64) PRIMARY KEY,project_id VARCHAR(64) NOT NULL,user_id VARCHAR(64) NOT NULL,action TEXT NOT NULL,details TEXT NOT NULL,created_at TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_conversations (id VARCHAR(64) PRIMARY KEY,project_id VARCHAR(64) NOT NULL,user_id VARCHAR(64) NOT NULL,title TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,busy_until DOUBLE PRECISION NOT NULL DEFAULT 0)',
    'CREATE TABLE IF NOT EXISTS v5_messages (id VARCHAR(64) PRIMARY KEY,conversation_id VARCHAR(64) NOT NULL,role VARCHAR(20) NOT NULL,content TEXT NOT NULL,status VARCHAR(20) NOT NULL,created_at TEXT NOT NULL,metadata TEXT NOT NULL)',
    'CREATE TABLE IF NOT EXISTS v5_usage (project_id VARCHAR(64) NOT NULL,day VARCHAR(10) NOT NULL,chat_requests INTEGER NOT NULL,PRIMARY KEY(project_id,day))',
    'CREATE TABLE IF NOT EXISTS v5_login_limits (key_hash VARCHAR(64) PRIMARY KEY,started_at DOUBLE PRECISION NOT NULL,attempts INTEGER NOT NULL)',
    'CREATE INDEX IF NOT EXISTS v5_messages_conversation ON v5_messages(conversation_id,created_at)',
    'CREATE INDEX IF NOT EXISTS v5_conversations_scope ON v5_conversations(project_id,user_id)',
    'CREATE INDEX IF NOT EXISTS v5_audit_scope ON v5_audit(project_id,created_at)',
]


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return 'scrypt$16384$8$1$' + salt.hex() + '$' + digest.hex()


def verify_password(password, encoded):
    try:
        _, n, r, p, salt, digest = encoded.split('$')
        actual = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(actual.hex(), digest)
    except (ValueError, TypeError):
        return False


class PlatformStore:
    def __init__(self, config):
        url = config.postgres_url
        config.store_path.mkdir(parents=True, exist_ok=True)
        self.kind = 'postgresql'
        # A configurable namespace supports isolated installations and real PG
        # test schemas, without a separate persistence implementation.
        namespace = config.database_schema
        if namespace and not re.fullmatch(r'cti_[a-z0-9_]{1,59}', namespace):
            raise ValueError('Invalid database schema.')
        if len(namespace)>54:
            namespace=namespace[:45]+'_'+hashlib.sha256(namespace.encode()).hexdigest()[:8]
        self.schema = (namespace + '_platform') if namespace else 'cti_platform'
        bootstrap_engine = create_engine(url, pool_pre_ping=True, connect_args={'connect_timeout':10})
        try:
            with bootstrap_engine.begin() as conn:
                conn.execute(text('CREATE SCHEMA IF NOT EXISTS ' + self.schema))
                conn.execute(text('REVOKE ALL ON SCHEMA ' + self.schema + ' FROM PUBLIC'))
        finally:
            bootstrap_engine.dispose()
        self.engine = create_engine(url, pool_pre_ping=True,
            connect_args={'connect_timeout':10,'options':'-csearch_path=' + self.schema})
        self.lock = threading.RLock()
        with self.transaction() as conn:
            for statement in SCHEMA:
                conn.execute(text(statement))

    @contextmanager
    def transaction(self):
        with self.lock:
            with self.engine.begin() as conn:
                yield conn

    def execute(self, sql, params=None, fetch=False):
        with self.transaction() as conn:
            result = conn.execute(text(sql), params or {})
            return [dict(row) for row in result.mappings().all()] if fetch else result.rowcount

    def one(self, sql, params=None):
        rows = self.execute(sql, params, True)
        return rows[0] if rows else None

    def rate_limit(self, key, limit=10, window=900):
        key = token_digest(key)
        stamp = time.time()
        with self.transaction() as conn:
            conn.execute(text('DELETE FROM v5_login_limits WHERE started_at<:cutoff'), {'cutoff':stamp-window})
            conn.execute(text('INSERT INTO v5_login_limits (key_hash,started_at,attempts) VALUES (:key,:stamp,0) ON CONFLICT(key_hash) DO NOTHING'), {'key':key,'stamp':stamp})
            count = conn.execute(text('UPDATE v5_login_limits SET attempts=attempts+1 WHERE key_hash=:key AND attempts<:limit'), {'key':key,'limit':limit}).rowcount
            return bool(count)
