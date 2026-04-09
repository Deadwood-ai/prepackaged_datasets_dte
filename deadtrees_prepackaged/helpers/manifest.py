from __future__ import annotations

from datetime import UTC, datetime


def build_manifest(
	dataset_name: str,
	package_name: str,
	version: str,
	used_dataset_ids: list[int],
	tree_cover_feature_count: int,
	dataset_count: int,
	artifact_names: list[str],
	test_mode: bool,
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
	}
