from deadtrees_prepackaged.helpers.license import (
	STANDING_DEADWOOD_MODEL_REFERENCE,
	TREE_COVER_REFERENCE,
	build_license_text,
)


def test_build_license_text_sorts_unique_authors_and_dois():
	license_text = build_license_text(
		[
			{
				'authors': ['Zed', 'Alice'],
				'citation_doi': '10.1000/zeta',
				'freidata_doi': '10.1000/gamma; 10.1000/beta',
			},
			{
				'authors': ['Alice', 'Bob'],
				'citation_doi': '10.1000/alpha',
				'freidata_doi': '10.1000/beta; 10.1000/delta',
			},
		],
		package_references=[TREE_COVER_REFERENCE, STANDING_DEADWOOD_MODEL_REFERENCE],
	)

	assert 'This package includes derivatives from aerial datasets created by the following authors.' in license_text
	assert 'Alice, Bob, Zed' in license_text
	assert 'https://deadtrees.earth, 10.1000/alpha, 10.1000/beta, 10.1000/delta, 10.1000/gamma, 10.1000/zeta' in license_text
	assert TREE_COVER_REFERENCE in license_text
	assert STANDING_DEADWOOD_MODEL_REFERENCE in license_text
	assert 'Creative Commons Attribution 4.0 International Public License' in license_text
