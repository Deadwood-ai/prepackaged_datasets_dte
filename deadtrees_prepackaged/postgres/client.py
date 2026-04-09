from __future__ import annotations

from contextlib import contextmanager

import psycopg

from ..config import BuildConfig


@contextmanager
def connect_postgres(config: BuildConfig):
	with psycopg.connect(**config.connection_kwargs()) as conn:
		yield conn
