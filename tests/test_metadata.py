from deadtrees_prepackaged.helpers.metadata import build_dataset_metadata_row


def test_metadata_row_omits_file_name():
	row = build_dataset_metadata_row(
		{
			'id': 123,
			'file_name': 'should_not_be_exported.tif',
			'authors': ['A', 'B'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'additional_information': 'info',
			'citation_doi': 'doi',
			'freidata_doi': 'freidata',
			'phenology_curve': '[7, 99]',
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'forest_cover_quality': 'great',
			'license': 'CC BY',
			'platform': 'aerial',
		}
	)

	assert 'file_name' not in row
	assert row['dataset_id'] == 123
	assert row['authors'] == 'A, B'
	assert row['phenology_probability_at_acquisition'] == 2.75
