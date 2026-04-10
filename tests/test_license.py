from deadtrees_prepackaged.helpers.license import build_license_text


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
		]
	)

	assert license_text == (
		'License: CC BY 4.0\n'
		'License URL: https://creativecommons.org/licenses/by/4.0/\n'
		'\n'
		'Authors:\n'
		'Alice\n'
		'Bob\n'
		'Zed\n'
		'\n'
		'Existing DOIs:\n'
		'10.1000/alpha\n'
		'10.1000/beta\n'
		'10.1000/delta\n'
		'10.1000/gamma\n'
		'10.1000/zeta\n'
	)
