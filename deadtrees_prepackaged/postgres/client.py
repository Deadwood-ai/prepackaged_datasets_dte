from __future__ import annotations

from contextlib import contextmanager

import psycopg

from ..config import BuildConfig


@contextmanager
def connect_postgres(config: BuildConfig):
	with psycopg.connect(**config.connection_kwargs(), prepare_threshold=None) as conn:
		conn.read_only = True
		yield conn
