from contextlib import contextmanager

from deadtrees_prepackaged.config import BuildConfig
from deadtrees_prepackaged.postgres.client import connect_postgres


class FakeConnection:
	def __init__(self):
		self.read_only = False

	def __enter__(self):
		return self

	def __exit__(self, exc_type, exc, tb):
		return False


def make_config() -> BuildConfig:
	return BuildConfig(
		pg_dsn='postgresql://user:pw@host:5432/db',
		pg_host=None,
		pg_port=None,
		pg_database=None,
		pg_user=None,
		pg_password=None,
		pg_sslmode=None,
		storage_root='/tmp',
		output_root='/tmp',
		working_dir='/tmp',
	)


def test_connect_postgres_sets_read_only(monkeypatch):
	fake_connection = FakeConnection()
	calls = {}

	def fake_connect(**kwargs):
		calls.update(kwargs)
		return fake_connection

	monkeypatch.setattr('deadtrees_prepackaged.postgres.client.psycopg.connect', fake_connect)

	with connect_postgres(make_config()) as conn:
		assert conn is fake_connection
		assert conn.read_only is True

	assert calls['conninfo'] == 'postgresql://user:pw@host:5432/db'
	assert calls['prepare_threshold'] is None
