from deadtrees_prepackaged.datasets.standing_deadwood_aerial_global_conservative import (
	_passes_phenology_filter,
)


def test_passes_phenology_filter_accepts_values_above_threshold():
	assert _passes_phenology_filter(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': '[129]',
		}
	)


def test_passes_phenology_filter_rejects_missing_or_low_values():
	assert not _passes_phenology_filter(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': '[128]',
		}
	)
	assert not _passes_phenology_filter(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': None,
		}
	)
