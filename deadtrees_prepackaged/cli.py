from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path

from .config import BuildConfig
from .runner import build_dataset, list_datasets


def _configure_logging() -> None:
	logging.basicConfig(
		level=logging.INFO,
		format='%(asctime)s %(levelname)s %(name)s: %(message)s',
	)


def _build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(description='Build prepackaged deadtrees datasets.')
	subparsers = parser.add_subparsers(dest='command', required=True)

	list_parser = subparsers.add_parser('list', help='List available dataset definitions')
	list_parser.set_defaults(func=_cmd_list)

	build_parser = subparsers.add_parser('build', help='Build a dataset definition')
	build_parser.add_argument('name', choices=list_datasets())
	build_parser.add_argument('--pg-dsn', default=os.getenv('DEADTREES_PG_DSN'))
	build_parser.add_argument('--pg-host', default=os.getenv('DEADTREES_DB_HOST'))
	build_parser.add_argument('--pg-port', type=int, default=int(os.getenv('DEADTREES_DB_PORT', '5432')))
	build_parser.add_argument('--pg-database', default=os.getenv('DEADTREES_DB_NAME'))
	build_parser.add_argument('--pg-user', default=os.getenv('DEADTREES_DB_USER'))
	build_parser.add_argument('--pg-password', default=os.getenv('DEADTREES_DB_PASSWORD'))
	build_parser.add_argument('--pg-sslmode', default=os.getenv('DEADTREES_DB_SSLMODE', 'disable'))
	build_parser.add_argument('--storage-root', required=True)
	build_parser.add_argument('--output-root', required=True)
	build_parser.add_argument('--working-dir', required=True)
	build_parser.add_argument('--version')
	build_parser.add_argument('--test-mode', action='store_true')
	build_parser.add_argument('--overwrite-existing', action='store_true')
	build_parser.add_argument('--keep-workdir', action='store_true')
	build_parser.set_defaults(func=_cmd_build)

	return parser


def _cmd_list(_args: argparse.Namespace) -> None:
	for name in list_datasets():
		print(name)


def _cmd_build(args: argparse.Namespace) -> None:
	config = BuildConfig(
		pg_dsn=args.pg_dsn,
		pg_host=args.pg_host,
		pg_port=args.pg_port,
		pg_database=args.pg_database,
		pg_user=args.pg_user,
		pg_password=args.pg_password,
		pg_sslmode=args.pg_sslmode,
		storage_root=Path(args.storage_root),
		output_root=Path(args.output_root),
		working_dir=Path(args.working_dir),
		version=args.version,
		test_mode=args.test_mode,
		overwrite_existing=args.overwrite_existing,
		keep_workdir=args.keep_workdir,
	)
	result = build_dataset(args.name, config)
	print(
		json.dumps(
			{
				'dataset_name': result.dataset_name,
				'package_name': result.package_name,
				'version': result.version,
				'output_dir': str(result.output_dir),
				'artifact_paths': {key: str(value) for key, value in result.artifact_paths.items()},
				'used_dataset_ids': result.used_dataset_ids,
				'dataset_metadata_rows': result.dataset_metadata_rows,
			},
			indent=2,
		)
	)


def main() -> None:
	_configure_logging()
	parser = _build_parser()
	args = parser.parse_args()
	args.func(args)


if __name__ == '__main__':
	main()
