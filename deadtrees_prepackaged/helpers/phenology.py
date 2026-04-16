from __future__ import annotations

import json
from datetime import date


def get_phenology_value_at_acquisition(
	dataset_row: dict,
	*,
	curve_field: str = 'phenology_curve',
) -> int | None:
	year = dataset_row.get('aquisition_year')
	month = dataset_row.get('aquisition_month')
	day = dataset_row.get('aquisition_day')
	phenology_curve = dataset_row.get(curve_field)

	if year is None or month is None or day is None or not phenology_curve:
		return None

	try:
		doy_index = date(int(year), int(month), int(day)).timetuple().tm_yday - 1
		curve = json.loads(phenology_curve)
		return int(curve[doy_index])
	except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
		return None


def passes_phenology_threshold(
	dataset_row: dict,
	*,
	threshold: int,
	curve_field: str = 'phenology_curve',
) -> bool:
	value = get_phenology_value_at_acquisition(
		dataset_row,
		curve_field=curve_field,
	)
	return value is not None and value > threshold
