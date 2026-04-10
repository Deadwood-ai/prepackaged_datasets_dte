from __future__ import annotations

import json
from datetime import date


def passes_phenology_threshold(
	dataset_row: dict,
	*,
	threshold: int,
	curve_field: str = 'phenology_curve',
) -> bool:
	year = dataset_row.get('aquisition_year')
	month = dataset_row.get('aquisition_month')
	day = dataset_row.get('aquisition_day')
	phenology_curve = dataset_row.get(curve_field)

	if year is None or month is None or day is None or not phenology_curve:
		return False

	try:
		doy_index = date(int(year), int(month), int(day)).timetuple().tm_yday - 1
		curve = json.loads(phenology_curve)
		value = curve[doy_index]
		return int(value) > threshold
	except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError):
		return False
