from __future__ import annotations


def public_cc_by_dataset_filters(
	*,
	dataset_alias: str = 'd',
	require_acquisition_date: bool = True,
) -> str:
	filters = [
		f"{dataset_alias}.license = 'CC BY'",
		f"{dataset_alias}.data_access = 'public'",
		f"coalesce({dataset_alias}.archived, false) = false",
	]

	if require_acquisition_date:
		filters.extend(
			[
				f'{dataset_alias}.aquisition_year is not null',
				f'{dataset_alias}.aquisition_month is not null',
				f'{dataset_alias}.aquisition_day is not null',
			]
		)

	return '\n\t\t\tand '.join(filters)


def public_cc_by_audited_candidate_filters(
	*,
	candidate_alias: str = 'p',
	dataset_alias: str = 'd',
	require_acquisition_date: bool = True,
) -> str:
	filters = [
		f"{candidate_alias}.final_assessment = 'no_issues'",
		public_cc_by_dataset_filters(
			dataset_alias=dataset_alias,
			require_acquisition_date=require_acquisition_date,
		),
	]
	return '\n\t\t\tand '.join(filters)
