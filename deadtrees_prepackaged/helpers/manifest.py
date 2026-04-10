from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path


DEFAULT_GITHUB_REPO_URL = 'https://github.com/Deadwood-ai/prepackaged_datasets_dte'
REPO_ROOT = Path(__file__).resolve().parents[2]


def _normalize_repo_url(repo_url: str) -> str:
	if repo_url.startswith('git@github.com:'):
		repo_path = repo_url.removeprefix('git@github.com:')
		if repo_path.endswith('.git'):
			repo_path = repo_path[:-4]
		return f'https://github.com/{repo_path}'
	if repo_url.startswith('https://github.com/') and repo_url.endswith('.git'):
		return repo_url[:-4]
	return repo_url


def _run_git_command(args: list[str]) -> str | None:
	try:
		completed = subprocess.run(
			['git', *args],
			check=True,
			capture_output=True,
			text=True,
			cwd=REPO_ROOT,
		)
	except (FileNotFoundError, subprocess.CalledProcessError):
		return None
	return completed.stdout.strip() or None


def get_source_commit() -> str | None:
	return (
		os.getenv('DEADTREES_SOURCE_COMMIT')
		or os.getenv('GITHUB_SHA')
		or _run_git_command(['rev-parse', 'HEAD'])
	)


def get_repo_url() -> str:
	repo_url = (
		os.getenv('DEADTREES_SOURCE_REPO_URL')
		or _run_git_command(['remote', 'get-url', 'origin'])
		or DEFAULT_GITHUB_REPO_URL
	)
	return _normalize_repo_url(repo_url)


def build_source_reference(source_file: str) -> dict:
	commit = get_source_commit()
	repo_url = get_repo_url()
	github_url = None
	if commit is not None:
		github_url = f'{repo_url}/blob/{commit}/{source_file}'

	return {
		'file': source_file,
		'commit': commit,
		'repository_url': repo_url,
		'github_url': github_url,
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
