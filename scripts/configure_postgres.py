"""Connect CTI to native PostgreSQL without Docker or database resets.

Run after SETUP_WINDOWS.bat. Passwords are read privately, never accepted as
command arguments or printed. Only DATABASE_URL is saved, after verification.
"""
from dataclasses import dataclass, field
import argparse
import getpass
import ipaddress
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit
import warnings

from dotenv import dotenv_values
import psycopg
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationError(Exception):
    """An operator-facing message that contains no server error or credentials."""


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Unsupported arguments. Use --check or --configure; passwords must be entered at the hidden local prompt.\n')


def validate_identifier(value):
    if not isinstance(value, str) or not value or len(value.encode('utf-8')) > 63 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ConfigurationError('Role and database names must contain 1–63 UTF-8 bytes and no control characters.')
    return value


def validate_port(value):
    if not re.fullmatch(r'[0-9]{1,5}', str(value)) or not 1 <= int(value) <= 65535:
        raise ConfigurationError('PostgreSQL port must be a whole number from 1 to 65535.')
    return int(value)


def validate_host(value):
    if not isinstance(value, str) or not value or len(value) > 253:
        raise ConfigurationError('Enter a PostgreSQL hostname or IP address without a URL or connection parameters.')
    try:
        ipaddress.ip_address(value)
        return value
    except ValueError:
        pass
    if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', value) or '..' in value:
        raise ConfigurationError('Enter a PostgreSQL hostname or IP address without a URL or connection parameters.')
    return value


def validate_password(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ConfigurationError('A nonempty application password without control characters is required.')
    return value


@dataclass(frozen=True)
class Connection:
    host: str
    port: int
    user: str
    password: str = field(repr=False)
    database: str
    options: tuple = field(default=(), repr=False)

    def __post_init__(self):
        validate_host(self.host)
        validate_port(self.port)
        validate_identifier(self.user)
        validate_identifier(self.database)
        if not isinstance(self.password, str) or any(ord(c) < 32 or ord(c) == 127 for c in self.password):
            raise ConfigurationError('The configured password contains unsupported control characters.')
        names = set()
        for name, value in self.options:
            if name in names or name.lower() in {'host', 'hostaddr', 'port', 'user', 'password', 'dbname', 'service', 'servicefile', 'passfile'}:
                raise ConfigurationError('URL query parameters cannot override the database endpoint or credentials.')
            if not re.fullmatch(r'[a-z_]+', name) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ConfigurationError('The database URL contains invalid connection options.')
            names.add(name)

    @classmethod
    def from_url(cls, value):
        try:
            # urlsplit silently removes some controls; reject them beforehand.
            if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
                raise ValueError()
            parsed = urlsplit(value)
            if parsed.scheme not in ('postgres', 'postgresql', 'postgresql+psycopg') or not parsed.hostname or not parsed.username or not parsed.path.startswith('/') or parsed.fragment:
                raise ValueError()
            return cls(parsed.hostname, 5432 if parsed.port is None else parsed.port, unquote(parsed.username),
                       unquote(parsed.password or ''), unquote(parsed.path[1:]),
                       tuple(parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)))
        except ConfigurationError:
            raise
        except (ValueError, TypeError, UnicodeError):
            raise ConfigurationError('DATABASE_URL must be a valid PostgreSQL URL with a host, role, port and database. Check your private .env.') from None

    def kwargs(self, database=None):
        values = dict(self.options)
        values.update(host=self.host, port=self.port, user=self.user, password=self.password,
                      dbname=database or self.database, connect_timeout=5)
        return values

    def url(self):
        host = '[' + self.host + ']' if ':' in self.host else self.host
        value = 'postgresql+psycopg://' + quote(self.user, safe='') + ':' + quote(self.password, safe='') + '@' + host + ':' + str(self.port) + '/' + quote(self.database, safe='')
        return value + ('?' + urlencode(self.options) if self.options else '')

    @property
    def local(self):
        return self.host.lower() == 'localhost' or self.host in ('127.0.0.1', '::1')


def read_env(path):
    # Literal ${...} in operator passwords must never be expanded.
    try:
        return dict(dotenv_values(path, interpolate=False, encoding='utf-8'))
    except (OSError, UnicodeError):
        raise ConfigurationError('Cannot read the private .env. Run SETUP_WINDOWS.bat first and check file permissions.') from None


def configuration(values):
    if values.get('DATABASE_URL'):
        return Connection.from_url(values['DATABASE_URL'])
    return Connection('127.0.0.1', validate_port(values.get('POSTGRES_PORT') or '5432'),
                      values.get('POSTGRES_USER') or 'cti', values.get('POSTGRES_PASSWORD') or '',
                      values.get('POSTGRES_DB') or 'cti')


def persist_url(path, url):
    """Replace only DATABASE_URL, atomically; keep other lines and line endings."""
    path = Path(path)
    if path.is_symlink():
        raise ConfigurationError('The private .env must be a regular file, not a symbolic link.')
    temporary = None
    try:
        with path.open('r', encoding='utf-8', newline='') as stream:
            contents = stream.read()
        newline = '\r\n' if '\r\n' in contents else '\n'
        # All URL components produced by Connection.url are percent encoded.
        if "'" in url or '\n' in url or '\r' in url:
            raise ConfigurationError('Cannot safely save the database URL.')
        replacement = "DATABASE_URL='" + url + "'"
        pattern = r'^[ \t]*(?:export[ \t]+)?DATABASE_URL[ \t]*=[^\r\n]*'
        if re.search(pattern, contents, flags=re.MULTILINE):
            contents = re.sub(pattern, lambda _: replacement, contents, flags=re.MULTILINE)
        else:
            contents += ('' if not contents or contents.endswith(('\n', '\r')) else newline) + replacement + newline
        descriptor, temporary = tempfile.mkstemp(prefix='.env-native-', dir=path.parent)
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        if os.name != 'nt':
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        temporary = None
    except (OSError, UnicodeError):
        raise ConfigurationError('The database login worked, but the private .env could not be saved. Check file permissions and retry.') from None
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def safe_database_error(error):
    # Do not include str(error): PostgreSQL and libpq may echo credentials/DSNs.
    state = getattr(error, 'sqlstate', None)
    if state in ('28P01', '28000'):
        return 'PostgreSQL rejected the login. Check the chosen role, password and server authentication settings.'
    if state == '3D000':
        return 'The selected PostgreSQL database does not exist.'
    if state == '42501':
        return 'PostgreSQL denied permission. The administrator needs CREATEROLE and CREATEDB for missing objects.'
    return 'PostgreSQL connection or setup failed. Check the service, host, port, credentials and TLS settings; server details are omitted to protect passwords.'


def verify_connection(connection):
    try:
        with psycopg.connect(**connection.kwargs()) as conn:
            identity = conn.execute('SELECT current_user, current_database()').fetchone()
            if identity != (connection.user, connection.database):
                raise ConfigurationError('The connection did not authenticate to the selected application role and database.')
    except psycopg.Error as error:
        raise ConfigurationError(safe_database_error(error)) from None


def provision(admin, app):
    """Create only missing objects, never ALTER ROLE or touch application data."""
    validate_password(app.password)
    if (admin.host, int(admin.port)) != (app.host, int(app.port)):
        raise ConfigurationError('Administrator and application must address the same PostgreSQL server.')
    created_role = created_database = False
    try:
        # CREATE DATABASE cannot execute inside a transaction.
        with psycopg.connect(**admin.kwargs(), autocommit=True) as conn:
            role_exists = conn.execute('SELECT 1 FROM pg_roles WHERE rolname = %s', (app.user,)).fetchone() is not None
            database_exists = conn.execute('SELECT 1 FROM pg_database WHERE datname = %s', (app.database,)).fetchone() is not None
            if role_exists:
                # Authenticate before creating a database for an existing role.
                # If the target is absent, use the maintenance DB for this check.
                probe = Connection(app.host, app.port, app.user, app.password,
                                   app.database if database_exists else admin.database, app.options)
                try:
                    verify_connection(probe)
                except ConfigurationError:
                    raise ConfigurationError('The existing role could not log in with the chosen application credentials. Its password was not changed. Rerun with operator-known application credentials or choose a new role name; also check CONNECT permission and authentication settings.') from None
            else:
                conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(app.user), sql.Literal(app.password)))
                created_role = True
            if not database_exists:
                conn.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(app.database), sql.Identifier(app.user)))
                created_database = True
        verify_connection(app)
    except psycopg.Error as error:
        raise ConfigurationError(safe_database_error(error)) from None
    return created_role, created_database


def secret_prompt(label):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            return getpass.getpass(label)
    except getpass.GetPassWarning:
        raise ConfigurationError('A private password prompt is unavailable. Run this helper directly in a local Windows terminal; do not pipe passwords.') from None


def prompt(label, default, validator):
    while True:
        value = input(label + ' [' + str(default) + ']: ').strip() or default
        try:
            return validator(value)
        except ConfigurationError as error:
            print(str(error))


def main(argv=None, root=ROOT):
    parser = PrivateArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Check the private DATABASE_URL without prompting or changing anything.')
    mode.add_argument('--configure', action='store_true', help='Choose connection settings explicitly, even when an existing URL works.')
    args = parser.parse_args(argv)
    path = Path(root) / '.env'
    try:
        if not path.is_file():
            raise ConfigurationError('Run SETUP_WINDOWS.bat first to install dependencies and create your private .env.')
        values = read_env(path)
        current = configuration(values)
        if not args.configure:
            try:
                verify_connection(current)
            except ConfigurationError as error:
                if args.check:
                    raise error
                if not current.local:
                    raise ConfigurationError('The existing remote DATABASE_URL could not be verified and has been preserved. Check it privately, or run CONNECT_DATABASE_WINDOWS.bat --configure to choose settings explicitly.') from None
                print('The current local database connection is not ready. Ensure PostgreSQL is installed and its Windows service is running.')
            else:
                print('Application database login verified. Existing private .env preserved. Next: START_WINDOWS.bat.')
                return 0
        print('Native PostgreSQL setup: only missing roles/databases are created. Existing passwords and data are preserved.')
        if not current.local:
            print('An existing remote URL is configured. Its connection options, including TLS, will be retained.')
            if input('Configure this connection explicitly? Type CONFIGURE to continue: ').strip() != 'CONFIGURE':
                print('Cancelled. Private .env preserved.')
                return 1
        host = prompt('PostgreSQL host', current.host, validate_host)
        port = prompt('PostgreSQL port', current.port, validate_port)
        user = prompt('Application role', current.user, validate_identifier)
        database = prompt('Application database', current.database, validate_identifier)
        password = secret_prompt('Application password (hidden; Enter keeps the private .env password): ') or current.password
        validate_password(password)
        app = Connection(host, port, user, password, database, current.options)
        admin_user = prompt('Administrator role', 'postgres', validate_identifier)
        admin_database = prompt('Administrator maintenance database', 'postgres', validate_identifier)
        admin_password = secret_prompt('PostgreSQL administrator password (hidden; never saved): ')
        admin = Connection(host, port, admin_user, admin_password, admin_database, current.options)
        created_role, created_database = provision(admin, app)
        persist_url(path, app.url())
        print('Application database login verified. DATABASE_URL saved in your private .env; administrator password was not saved.')
        print('Role: ' + ('created' if created_role else 'existing, preserved') + '. Database: ' + ('created' if created_database else 'existing, preserved') + '.')
        print('Next: START_WINDOWS.bat. Keep .env private; use its SETUP_TOKEN for the first owner account.')
        return 0
    except ConfigurationError as error:
        print(str(error))
        print('Setup did not finish. No existing role password or database was reset. Retry after correcting the settings.')
        return 1
    except (EOFError, KeyboardInterrupt):
        print('\nCancelled. No administrator password was saved.')
        return 1
    except Exception:
        # Library/filesystem failures must not cause a traceback containing secrets.
        print('Setup did not finish. Details are hidden to protect credentials. Check local settings and retry; no existing password or database was reset.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
