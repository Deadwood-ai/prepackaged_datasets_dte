from deadtrees_prepackaged.helpers.phenology import (
	get_phenology_value_at_acquisition,
	passes_phenology_threshold,
)


def test_get_phenology_value_at_acquisition_returns_value_for_acquisition_day():
	assert get_phenology_value_at_acquisition(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'phenology_curve': '[10, 42]',
		}
	) == 42


def test_get_phenology_value_at_acquisition_returns_none_on_missing_or_invalid_data():
	assert get_phenology_value_at_acquisition(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 1,
			'phenology_curve': None,
		}
	) is None
	assert get_phenology_value_at_acquisition(
		{
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 3,
			'phenology_curve': '[10, 42]',
		}
	) is None


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
