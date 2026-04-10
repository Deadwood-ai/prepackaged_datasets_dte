from deadtrees_prepackaged.helpers.phenology import passes_phenology_threshold


def test_passes_phenology_filter_accepts_values_above_threshold():
	assert passes_phenology_threshold(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': '[129]',
		},
		threshold=128,
	)


def test_passes_phenology_filter_rejects_missing_or_low_values():
	assert not passes_phenology_threshold(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': '[128]',
		},
		threshold=128,
	)
	assert not passes_phenology_threshold(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': None,
		},
		threshold=128,
	)
