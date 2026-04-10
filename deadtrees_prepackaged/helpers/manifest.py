from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as get_installed_version
from datetime import UTC, datetime


PACKAGE_NAME = 'deadtrees-prepackaged'

def get_package_version() -> str | None:
	try:
		return get_installed_version(PACKAGE_NAME)
	except PackageNotFoundError:
		return None


def build_source_reference(source_file: str) -> dict:
	return {
		'file': source_file,
		'package_version': get_package_version(),
	}


def build_manifest(
	dataset_name: str,
	package_name: str,
	version: str,
	used_dataset_ids: list[int],
	tree_cover_feature_count: int,
	dataset_count: int,
	artifact_names: list[str],
	test_mode: bool,
	source_file: str,
) -> dict:
	return {
		'dataset_name': dataset_name,
		'package_name': package_name,
		'version': version,
		'test_mode': test_mode,
		'built_at': datetime.now(UTC).isoformat(),
		'used_dataset_ids': used_dataset_ids,
		'dataset_count': dataset_count,
		'tree_cover_feature_count': tree_cover_feature_count,
		'artifacts': artifact_names,
		'source_reference': build_source_reference(source_file),
	}
