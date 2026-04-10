from __future__ import annotations


CC_BY_LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'


def _collect_authors(dataset_rows: list[dict]) -> list[str]:
	authors = {
		author.strip()
		for dataset_row in dataset_rows
		for author in (dataset_row.get('authors') or [])
		if author and author.strip()
	}
	return sorted(authors)


def _collect_dois(dataset_rows: list[dict]) -> list[str]:
	dois: set[str] = set()
	for dataset_row in dataset_rows:
		citation_doi = dataset_row.get('citation_doi')
		if citation_doi:
			dois.add(str(citation_doi).strip())

		freidata_doi = dataset_row.get('freidata_doi')
		if not freidata_doi:
			continue
		for doi in str(freidata_doi).split(';'):
			doi = doi.strip()
			if doi:
				dois.add(doi)

	return sorted(dois)


def build_license_text(dataset_rows: list[dict]) -> str:
	authors = _collect_authors(dataset_rows)
	dois = _collect_dois(dataset_rows)

	lines = [
		'License: CC BY 4.0',
		f'License URL: {CC_BY_LICENSE_URL}',
	]

	if authors:
		lines.extend(
			[
				'',
				'Authors:',
				*authors,
			]
		)

	if dois:
		lines.extend(
			[
				'',
				'Existing DOIs:',
				*dois,
			]
		)

	return '\n'.join(lines) + '\n'
