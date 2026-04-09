from __future__ import annotations


def build_dataset_metadata_row(dataset_row: dict) -> dict:
	return {
		'dataset_id': dataset_row['id'],
		'authors': ', '.join(dataset_row.get('authors') or []),
		'acquisition_year': dataset_row.get('aquisition_year'),
		'acquisition_month': dataset_row.get('aquisition_month'),
		'acquisition_day': dataset_row.get('aquisition_day'),
		'additional_information': dataset_row.get('additional_information'),
		'citation_doi': dataset_row.get('citation_doi'),
		'freidata_doi': dataset_row.get('freidata_doi'),
		'bbox': dataset_row.get('bbox'),
		'biome_name': dataset_row.get('biome_name'),
		'forest_cover_quality': dataset_row.get('forest_cover_quality'),
		'license': dataset_row.get('license'),
		'platform': dataset_row.get('platform'),
	}
