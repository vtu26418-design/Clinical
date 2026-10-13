"""Server-only settings. Relative storage paths are anchored to the project root."""
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_env: str = 'development'
    auth_mode: Literal['session', 'local'] = 'session'
    setup_token: str = Field(default='', repr=False)
    session_hours: int = Field(default=12, ge=1, le=168)
    require_email_verification: bool = False
    mail_api_key: str = Field(default='', repr=False)
    mail_from: str = ''
    public_base_url: str = ''
    database_schema: str = ''
    trusted_proxy_hosts: str = ''
    rate_limit_requests: int = Field(default=60, ge=1, le=10000)
    rate_limit_training: int = Field(default=10, ge=1, le=1000)
    rate_limit_assistant: int = Field(default=30, ge=1, le=1000)
    ai_max_output_tokens: int = Field(default=16000, ge=100, le=65536)
    ai_context_chars: int = Field(default=120000, ge=2000, le=262144)
    import_allowed_hosts: str = 'clinicaltrials.gov,raw.githubusercontent.com'
    max_projects_per_user: int = Field(default=30, ge=1, le=200)
    max_conversations_per_user: int = Field(default=200, ge=1, le=1000)
    max_messages_per_conversation: int = Field(default=200, ge=2, le=2000)
    api_host: str = '127.0.0.1'
    api_port: int = 8000
    cors_origins: str = 'http://localhost:5173,http://127.0.0.1:5173'
    storage_dir: str = './data/workbench'
    database_url: str = Field(default='', repr=False)
    aact_snapshot_path: str = './data/raw/aact_snapshot'
    processed_data_path: str = './data/processed'
    openai_api_key: str = Field(default='', repr=False)
    openai_model: str = 'gpt-6.1-sol'
    gemini_api_key: str = Field(default='', repr=False)
    gemini_model: str = 'gemini-3.8-flash'
    anthropic_api_key: str = Field(default='', repr=False)
    anthropic_model: str = 'claude-sonnet-5-5'
    compatible_api_key: str = Field(default='', repr=False)
    compatible_base_url: str = ''
    compatible_model: str = ''
    ai_provider: Literal['auto', 'openai', 'anthropic', 'gemini', 'compatible'] = 'auto'
    ai_provider_priority: str = 'openai,anthropic,gemini,compatible'
    ai_auto_fallback: bool = True
    api_bearer_token: str = Field(default='', repr=False)
    max_upload_bytes: int = Field(25 * 1024 * 1024, ge=1024, le=100 * 1024 * 1024)
    max_dataset_rows: int = Field(100_000, ge=30, le=1_000_000)
    max_training_rows: int = Field(20_000, ge=30, le=100_000)
    frontend_dist: str = './frontend/dist'
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / '.env'), extra='ignore')

    @field_validator('ai_provider', mode='before')
    @classmethod
    def provider_alias(cls, value):
        value = str(value).strip().lower()
        return 'anthropic' if value == 'claude' else value

    @field_validator('ai_provider_priority')
    @classmethod
    def provider_order(cls, value):
        names = [cls.provider_alias(part) for part in value.split(',') if part.strip()]
        if not names or any(name not in {'openai', 'anthropic', 'gemini', 'compatible'} for name in names):
            raise ValueError('Use a comma-separated order of openai, anthropic, gemini, compatible.')
        return ','.join(dict.fromkeys(names))

    @field_validator('compatible_base_url')
    @classmethod
    def compatible_endpoint(cls, value):
        value = value.strip().rstrip('/')
        if not value:
            return value
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('COMPATIBLE_BASE_URL must be HTTPS without credentials, query or fragment.')
        return value

    @field_validator('public_base_url')
    @classmethod
    def public_endpoint(cls, value):
        value = value.strip().rstrip('/')
        if not value:
            return value
        parsed = urlsplit(value)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('PUBLIC_BASE_URL must be HTTPS without credentials, query or fragment.')
        return value

    def path(self, value: str) -> Path:
        path = Path(value).expanduser()
        return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()

    @property
    def store_path(self) -> Path:
        return self.path(self.storage_dir)

    @property
    def postgres_url(self) -> str:
        """Require the same PostgreSQL backend in every application mode."""
        value = self.database_url.strip()
        if value.startswith('postgres://'):
            value = 'postgresql+psycopg://' + value[len('postgres://'):]
        elif value.startswith('postgresql://'):
            value = 'postgresql+psycopg://' + value[len('postgresql://'):]
        if not value.startswith('postgresql+psycopg://'):
            raise ValueError('PostgreSQL DATABASE_URL is required. Run setup and configure PostgreSQL before starting the application.')
        parsed = urlsplit(value)
        if not parsed.hostname or not parsed.path.strip('/'):
            raise ValueError('PostgreSQL DATABASE_URL must include a server and database name.')
        return value

    @field_validator('database_schema')
    @classmethod
    def private_schema(cls, value):
        import re
        if value and not re.fullmatch(r'cti_[a-z0-9_]{1,59}', value):
            raise ValueError('Invalid database schema; use a private cti_ schema of at most 63 characters.')
        return value


settings = Settings()
