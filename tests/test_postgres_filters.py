from deadtrees_prepackaged.postgres.filters import public_cc_by_audited_candidate_filters


def test_public_cc_by_audited_candidate_filters_include_audited_constraint():
	filters = public_cc_by_audited_candidate_filters(candidate_alias='p', dataset_alias='d')

	assert "p.final_assessment = 'no_issues'" in filters
	assert "d.license = 'CC BY'" in filters
	assert "d.data_access = 'public'" in filters
	assert 'coalesce(d.archived, false) = false' in filters
