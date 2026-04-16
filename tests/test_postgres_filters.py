from deadtrees_prepackaged.postgres.filters import public_cc_by_dataset_filters


def test_public_cc_by_dataset_filters_require_audited_no_issues_by_default():
	filters = public_cc_by_dataset_filters(dataset_alias='d')

	assert "d.final_assessment = 'no_issues'" in filters
	assert "d.license = 'CC BY'" in filters
	assert "d.data_access = 'public'" in filters
	assert 'coalesce(d.archived, false) = false' in filters
