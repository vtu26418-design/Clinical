"""Focused native setup checks; no app schemas or databases are touched.

Run: python -m unittest discover -s tests -p test_native_postgres_v5203.py
Optional TEST_DATABASE_URL must address a disposable PostgreSQL administrator.
Each integration test owns uniquely named roles/databases and cleans only those.
"""
import importlib.util
import contextlib
import io
import os
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import uuid

import psycopg
from psycopg import sql


HELPER = Path(__file__).parents[1] / 'scripts' / 'configure_postgres.py'


def helper():
    spec = importlib.util.spec_from_file_location('configure_postgres', HELPER)
    module = importlib.util.module_from_spec(spec)
    # dataclasses resolve the module through sys.modules.
    import sys
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class NativeConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(HELPER.exists(), 'The native PostgreSQL helper is missing')
        self.m = helper()

    def test_url_roundtrip_encodes_credentials_and_keeps_tls(self):
        c = self.m.Connection('db.example.com', 6543, 'role " /@', 'p@:/?#%$é',
                              'db " /', (('sslmode', 'verify-full'), ('sslrootcert', 'C:/certs/a b.pem')))
        url = c.url()
        self.assertNotIn(c.password, url)
        parsed = self.m.Connection.from_url(url)
        self.assertEqual((parsed.host, parsed.port, parsed.user, parsed.password, parsed.database, parsed.options),
                         (c.host, c.port, c.user, c.password, c.database, c.options))
        self.assertNotIn(c.password, repr(c))
        self.assertIn('sslmode=verify-full', url)

    def test_env_parse_does_not_expand_password_or_touch_other_settings(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            original = '# Private\r\nSETUP_TOKEN=keep-owner\r\nPOSTGRES_PASSWORD="literal${SECRET}"\r\nOPENAI_API_KEY=keep-model\r\nCOMPOSE_DATABASE_URL=keep-compose\r\nexport DATABASE_URL = "old" # native\r\n'
            path.write_bytes(original.encode())
            values = self.m.read_env(path)
            self.assertEqual(values['POSTGRES_PASSWORD'], 'literal${SECRET}')
            self.m.persist_url(path, 'postgresql+psycopg://r:p@127.0.0.1:5432/d')
            content = path.read_bytes().decode()
            self.assertEqual(content, original.replace('export DATABASE_URL = "old" # native', "DATABASE_URL='postgresql+psycopg://r:p@127.0.0.1:5432/d'"))
            if os.name != 'nt':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_defaults_take_operator_local_url_over_compose_values(self):
        c = self.m.configuration({'DATABASE_URL': 'postgresql+psycopg://chosen:private@localhost:6543/research?sslmode=require',
                                  'POSTGRES_USER': 'cti', 'POSTGRES_DB': 'cti', 'POSTGRES_PASSWORD': 'generated'})
        self.assertEqual((c.host, c.port, c.user, c.password, c.database), ('localhost', 6543, 'chosen', 'private', 'research'))
        self.assertEqual(c.options, (('sslmode', 'require'),))

    def test_generated_defaults_and_ipv6(self):
        c = self.m.configuration({'POSTGRES_PASSWORD': 'private'})
        self.assertEqual((c.host, c.port, c.user, c.database), ('127.0.0.1', 5432, 'cti', 'cti'))
        c = self.m.Connection('::1', 5432, 'cti', 'private', 'cti')
        self.assertEqual(self.m.Connection.from_url(c.url()).host, '::1')

    def test_input_validation(self):
        for port in ('0', '65536', 'abc', '-1', '5432.0'):
            with self.subTest(port=port), self.assertRaises(self.m.ConfigurationError):
                self.m.validate_port(port)
        for name in ('', 'a' * 64, 'é' * 32, 'bad\x00name', 'bad\nname'):
            with self.subTest(name=name), self.assertRaises(self.m.ConfigurationError):
                self.m.validate_identifier(name)
        for host in ('', 'a/b', 'a@b', 'a b', 'bad\n', 'x;password=secret'):
            with self.subTest(host=host), self.assertRaises(self.m.ConfigurationError):
                self.m.validate_host(host)
        self.assertEqual(self.m.validate_identifier('role " ; quoted'), 'role " ; quoted')

    def test_bad_url_and_database_errors_never_reveal_secrets(self):
        secret = 'sensitive-password'
        for url in (f'postgresql://cti:{secret}@localhost:bad/db', f'sqlite://{secret}',
                    f'postgresql://cti:{secret}@/db', f'postgresql://cti:{secret}@localhost:0/db',
                    f'postgresql://cti:{secret}@localhost/db?password=override'):
            with self.subTest(url=url), self.assertRaises(self.m.ConfigurationError) as error:
                self.m.Connection.from_url(url)
            self.assertNotIn(secret, str(error.exception))
        with patch.object(self.m.psycopg, 'connect', side_effect=psycopg.OperationalError(f'DSN={secret}')):
            with self.assertRaises(self.m.ConfigurationError) as error:
                self.m.verify_connection(self.m.Connection('127.0.0.1', 5432, 'cti', secret, 'cti'))
            self.assertNotIn(secret, str(error.exception))

    def test_secret_argument_errors_do_not_echo_argument_values(self):
        output = io.StringIO()
        with contextlib.redirect_stderr(output), self.assertRaises(SystemExit) as error:
            self.m.main(['--password', 'do-not-print-me'])
        self.assertEqual(error.exception.code, 2)
        self.assertNotIn('do-not-print-me', output.getvalue())

    def test_check_does_not_prompt_even_for_failed_local_connection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            original = 'DATABASE_URL=postgresql+psycopg://cti:private@127.0.0.1:5432/cti\n'
            path.write_text(original)
            with contextlib.redirect_stdout(io.StringIO()), patch.object(self.m, 'verify_connection', side_effect=self.m.ConfigurationError('unreachable')), patch('builtins.input', side_effect=AssertionError('check never prompts')):
                self.assertEqual(self.m.main(['--check'], root=Path(folder)), 1)
            self.assertEqual(path.read_text(), original)

    def test_echoing_getpass_fallback_is_rejected(self):
        import getpass
        import warnings
        def echoing_prompt(label):
            warnings.warn('Password input may echo', getpass.GetPassWarning)
            return 'never-read'
        with patch.object(self.m.getpass, 'getpass', side_effect=echoing_prompt):
            with self.assertRaises(self.m.ConfigurationError) as error:
                self.m.secret_prompt('hidden: ')
        self.assertIn('private password prompt', str(error.exception))

    def test_working_url_needs_no_admin_and_does_not_change_env(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            original = 'DATABASE_URL=postgresql+psycopg://cti:private@127.0.0.1:5432/cti\n'
            path.write_text(original)
            with contextlib.redirect_stdout(io.StringIO()), patch.object(self.m, 'verify_connection'), patch.object(self.m, 'secret_prompt', side_effect=AssertionError('no admin needed')):
                self.assertEqual(self.m.main([], root=Path(folder)), 0)
            self.assertEqual(path.read_text(), original)

    def test_remote_failure_does_not_prompt_or_replace_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            original = 'DATABASE_URL=postgresql+psycopg://cti:private@remote.invalid:5432/cti?sslmode=verify-full\n'
            path.write_text(original)
            with contextlib.redirect_stdout(io.StringIO()), patch.object(self.m, 'verify_connection', side_effect=self.m.ConfigurationError('unreachable')), patch.object(self.m, 'secret_prompt', side_effect=AssertionError('remote config preserved')):
                self.assertEqual(self.m.main([], root=Path(folder)), 1)
            self.assertEqual(path.read_text(), original)


@unittest.skipUnless(os.environ.get('TEST_DATABASE_URL'), 'Set TEST_DATABASE_URL for disposable PostgreSQL integration')
class NativePostgresLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.m = helper()
        self.admin = self.m.Connection.from_url(os.environ['TEST_DATABASE_URL'])
        self.admin_conn = psycopg.connect(**self.admin.kwargs(), autocommit=True)
        privileges = self.admin_conn.execute('SELECT rolsuper, rolcreaterole, rolcreatedb FROM pg_roles WHERE rolname = current_user').fetchone()
        if not privileges or not (privileges[0] or (privileges[1] and privileges[2])):
            self.admin_conn.close()
            self.skipTest('Disposable administrator requires CREATEROLE and CREATEDB')
        self.role = 'cti_native_' + uuid.uuid4().hex[:12] + ' "'
        self.database = 'cti_native_' + uuid.uuid4().hex[:12] + ' "'
        self.password = secrets.token_urlsafe(24) + "'@:/?#%$"
        self.app = self.m.Connection(self.admin.host, self.admin.port, self.role, self.password,
                                     self.database, self.admin.options)

    def tearDown(self):
        if getattr(self, 'admin_conn', None) and not self.admin_conn.closed:
            # Only this test's randomly named objects, never an existing app DB.
            self.admin_conn.execute(sql.SQL('DROP DATABASE IF EXISTS {}').format(sql.Identifier(self.database)))
            self.admin_conn.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(self.role)))
            self.admin_conn.close()

    def test_create_verify_repeat_preserves_database_contents(self):
        result = self.m.provision(self.admin, self.app)
        self.assertEqual(result, (True, True))
        with psycopg.connect(**self.app.kwargs()) as conn:
            conn.execute('CREATE TABLE native_setup_evidence (value text)')
            conn.execute('INSERT INTO native_setup_evidence VALUES (%s)', ('keep-existing',))
        self.assertEqual(self.m.provision(self.admin, self.app), (False, False))
        with psycopg.connect(**self.app.kwargs()) as conn:
            self.assertEqual(conn.execute('SELECT value FROM native_setup_evidence').fetchone(), ('keep-existing',))
        self.m.verify_connection(self.m.Connection.from_url(self.app.url()))

    def test_wrong_existing_password_creates_no_database_and_keeps_role(self):
        self.admin_conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {}').format(sql.Identifier(self.role), sql.Literal(self.password)))
        wrong = self.m.Connection(self.app.host, self.app.port, self.role, 'wrong-private-password', self.database, self.app.options)
        with self.assertRaises(self.m.ConfigurationError) as error:
            self.m.provision(self.admin, wrong)
        self.assertIn('existing role', str(error.exception).lower())
        self.assertNotIn('wrong-private-password', str(error.exception))
        self.assertIsNone(self.admin_conn.execute('SELECT 1 FROM pg_database WHERE datname = %s', (self.database,)).fetchone())
        # The correct password still authenticates; no ALTER ROLE occurred.
        good = self.m.Connection(self.app.host, self.app.port, self.role, self.password, self.admin.database, self.app.options)
        self.m.verify_connection(good)

    def test_cli_saves_only_verified_app_url_and_never_admin_password(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            app_url = self.app.url()
            original = "DATABASE_URL='" + app_url + "'\nSETUP_TOKEN=private-owner\nOPENAI_API_KEY=keep-model\nCOMPOSE_DATABASE_URL=keep-compose\n"
            path.write_text(original)
            output = io.StringIO()
            # Explicit configuration skips the initial successful-login shortcut.
            answers = [''] * 4 + [self.admin.user, self.admin.database]
            if not self.app.local:
                answers.insert(0, 'CONFIGURE')
            with patch('builtins.input', side_effect=answers), patch.object(self.m, 'secret_prompt', side_effect=['', self.admin.password]), contextlib.redirect_stdout(output):
                self.assertEqual(self.m.main(['--configure'], root=Path(folder)), 0)
            self.assertEqual(path.read_text(), original)
            self.assertNotIn(self.password, output.getvalue())
            if self.admin.password:
                self.assertNotIn(self.admin.password, path.read_text())
                self.assertNotIn(self.admin.password, output.getvalue())
            with patch('builtins.input', side_effect=AssertionError('no prompts')), contextlib.redirect_stdout(output):
                self.assertEqual(self.m.main(['--check'], root=Path(folder)), 0)

    def test_cli_auth_failure_leaves_private_env_unchanged(self):
        self.m.provision(self.admin, self.app)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            original = "DATABASE_URL='" + self.app.url() + "'\nSETUP_TOKEN=private-owner\nOPENAI_API_KEY=keep-model\n"
            path.write_text(original)
            answers = [''] * 4 + [self.admin.user, self.admin.database]
            if not self.app.local:
                answers.insert(0, 'CONFIGURE')
            output = io.StringIO()
            with patch('builtins.input', side_effect=answers), patch.object(self.m, 'secret_prompt', side_effect=['wrong-private-password', self.admin.password]), contextlib.redirect_stdout(output):
                self.assertEqual(self.m.main(['--configure'], root=Path(folder)), 1)
            self.assertEqual(path.read_text(), original)
            self.assertNotIn('wrong-private-password', output.getvalue())
            self.m.verify_connection(self.app)


if __name__ == '__main__':
    unittest.main()
