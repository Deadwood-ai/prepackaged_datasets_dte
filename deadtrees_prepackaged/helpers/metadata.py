from __future__ import annotations

from .phenology import get_phenology_value_at_acquisition


def _normalize_phenology_probability(raw_value: int | None) -> float | None:
	if raw_value is None:
		return None
	return round((float(raw_value) / 255.0) * 100.0, 2)


def build_dataset_metadata_row(dataset_row: dict) -> dict:
	phenology_value = get_phenology_value_at_acquisition(dataset_row)
	return {
		'dataset_id': dataset_row['id'],
		'authors': ', '.join(dataset_row.get('authors') or []),
		'acquisition_year': dataset_row.get('aquisition_year'),
		'acquisition_month': dataset_row.get('aquisition_month'),
		'acquisition_day': dataset_row.get('aquisition_day'),
		'additional_information': dataset_row.get('additional_information'),
		'citation_doi': dataset_row.get('citation_doi'),
		'freidata_doi': dataset_row.get('freidata_doi'),
		'phenology_probability_at_acquisition': _normalize_phenology_probability(phenology_value),
		'bbox': dataset_row.get('bbox'),
		'biome_name': dataset_row.get('biome_name'),
		'forest_cover_quality': dataset_row.get('forest_cover_quality'),
		'license': dataset_row.get('license'),
		'platform': dataset_row.get('platform'),
	}
