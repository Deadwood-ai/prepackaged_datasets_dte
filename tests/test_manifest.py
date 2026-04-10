from deadtrees_prepackaged.helpers import manifest


def test_build_source_reference_uses_env_without_git(monkeypatch):
	monkeypatch.setenv('DEADTREES_SOURCE_COMMIT', 'abc123')
	monkeypatch.setenv(
		'DEADTREES_SOURCE_REPO_URL',
		'https://github.com/Deadwood-ai/prepackaged_datasets_dte',
	)
	monkeypatch.setattr(manifest, '_run_git_command', lambda _args: None)

	source_reference = manifest.build_source_reference(
		'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
	)

	assert source_reference == {
		'file': 'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py',
		'commit': 'abc123',
		'repository_url': 'https://github.com/Deadwood-ai/prepackaged_datasets_dte',
		'github_url': (
			'https://github.com/Deadwood-ai/prepackaged_datasets_dte/blob/abc123/'
			'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
		),
	}


def test_build_source_reference_still_works_without_commit(monkeypatch):
	monkeypatch.delenv('DEADTREES_SOURCE_COMMIT', raising=False)
	monkeypatch.delenv('GITHUB_SHA', raising=False)
	monkeypatch.delenv('DEADTREES_SOURCE_REPO_URL', raising=False)
	monkeypatch.setattr(manifest, '_run_git_command', lambda _args: None)

	source_reference = manifest.build_source_reference(
		'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
	)

	assert source_reference == {
		'file': 'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py',
		'commit': None,
		'repository_url': 'https://github.com/Deadwood-ai/prepackaged_datasets_dte',
		'github_url': None,
	}
