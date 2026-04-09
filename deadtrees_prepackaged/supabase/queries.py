from __future__ import annotations

from supabase import Client


def fetch_eligible_tree_cover_datasets(client: Client) -> list[dict]:
	response = (
		client.table('v2_full_dataset_view_public')
		.select(
			'id, file_name, authors, aquisition_year, aquisition_month, aquisition_day, '
			'additional_information, citation_doi, freidata_doi, bbox, biome_name, '
			'forest_cover_quality, license, platform, is_audited'
		)
		.eq('license', 'CC BY')
		.eq('is_audited', True)
		.execute()
	)
	rows = response.data or []
	return [
		row for row in rows
		if row.get('forest_cover_quality') in {'great', 'sentinel_ok'}
	]
