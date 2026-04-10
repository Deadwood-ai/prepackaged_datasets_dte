from deadtrees_prepackaged.helpers import manifest


def test_build_source_reference_includes_package_version(monkeypatch):
	monkeypatch.setattr(manifest, 'get_package_version', lambda: '0.1.0')

	source_reference = manifest.build_source_reference(
		'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
	)

	assert source_reference == {
		'file': 'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py',
		'package_version': '0.1.0',
	}


def test_build_source_reference_still_works_without_package_metadata(monkeypatch):
	monkeypatch.setattr(manifest, 'get_package_version', lambda: None)

	source_reference = manifest.build_source_reference(
		'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
	)

	assert source_reference == {
		'file': 'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py',
		'package_version': None,
	}
