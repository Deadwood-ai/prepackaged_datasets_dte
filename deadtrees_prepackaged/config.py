from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class BuildConfig:
	pg_dsn: str | None
	pg_host: str | None
	pg_port: int | None
	pg_database: str | None
	pg_user: str | None
	pg_password: str | None
	pg_sslmode: str | None
	storage_root: Path | str
	output_root: Path | str
	working_dir: Path | str
	version: str | None = None
	test_mode: bool = False
	overwrite_existing: bool = False
	keep_workdir: bool = False

	def __post_init__(self) -> None:
		self.storage_root = Path(self.storage_root)
		self.output_root = Path(self.output_root)
		self.working_dir = Path(self.working_dir)

	def connection_kwargs(self) -> dict:
		if self.pg_dsn:
			return {'conninfo': self.pg_dsn}

		missing = [
			name for name, value in {
				'pg_host': self.pg_host,
				'pg_port': self.pg_port,
				'pg_database': self.pg_database,
				'pg_user': self.pg_user,
				'pg_password': self.pg_password,
			}.items()
			if value in (None, '')
		]
		if missing:
			raise ValueError(f'Missing PostgreSQL config fields: {", ".join(missing)}')

		return {
			'host': self.pg_host,
			'port': self.pg_port,
			'dbname': self.pg_database,
			'user': self.pg_user,
			'password': self.pg_password,
			'sslmode': self.pg_sslmode or 'disable',
		}
