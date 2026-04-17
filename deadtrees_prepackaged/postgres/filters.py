from __future__ import annotations


def public_cc_by_dataset_filters(
	*,
	dataset_alias: str = 'd',
	require_acquisition_date: bool = True,
	require_audited_no_issues: bool = True,
) -> str:
	filters = [
		f"{dataset_alias}.license = 'CC BY'",
		f"{dataset_alias}.data_access = 'public'",
		f"coalesce({dataset_alias}.archived, false) = false",
	]

	if require_audited_no_issues:
		filters.extend(
			[
				f"coalesce({dataset_alias}.is_audited, false) = true",
				(
					"exists ("
					"select 1 "
					"from dataset_audit da "
					f"where da.dataset_id = {dataset_alias}.id "
					"and da.final_assessment = 'no_issues'"
					")"
				),
			]
		)

	if require_acquisition_date:
		filters.extend(
			[
				f'{dataset_alias}.aquisition_year is not null',
				f'{dataset_alias}.aquisition_month is not null',
				f'{dataset_alias}.aquisition_day is not null',
			]
		)

	return '\n\t\t\tand '.join(filters)
