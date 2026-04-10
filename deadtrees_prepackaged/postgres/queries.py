from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row


def fetch_eligible_tree_cover_datasets(connection: Connection, limit: int | None = None) -> list[dict]:
	sql = """
		with eligible as (
			select distinct
				p.dataset_id
			from v_export_polygon_candidates p
			join v2_datasets d on d.id = p.dataset_id
			where p.layer_type = 'forest_cover'
				and p.forest_cover_quality in ('great', 'sentinel_ok')
				and d.license = 'CC BY'
				and d.data_access = 'public'
		),
		doi_info as (
			select
				jt.dataset_id,
				string_agg(distinct dp.doi, '; ' order by dp.doi) as freidata_doi
			from jt_data_publication_datasets jt
			join data_publication dp on dp.id = jt.publication_id
			where dp.doi is not null
			group by jt.dataset_id
		),
		quality_info as (
			select
				dataset_id,
				min(forest_cover_quality) as forest_cover_quality
			from v_export_polygon_candidates
			where layer_type = 'forest_cover'
			group by dataset_id
		)
		select
			d.id,
			d.file_name,
			d.authors,
			d.aquisition_year,
			d.aquisition_month,
			d.aquisition_day,
			d.additional_information,
			d.citation_doi,
			o.bbox::text as bbox,
			(m.metadata -> 'biome' ->> 'biome_name') as biome_name,
			q.forest_cover_quality,
			d.license::text as license,
			d.platform::text as platform,
			di.freidata_doi
		from eligible e
		join v2_datasets d on d.id = e.dataset_id
		left join v2_orthos o on o.dataset_id = d.id
		left join v2_metadata m on m.dataset_id = d.id
		left join quality_info q on q.dataset_id = d.id
		left join doi_info di on di.dataset_id = d.id
		order by d.id
	"""
	params: tuple = ()
	if limit is not None:
		sql += "\nlimit %s"
		params = (limit,)

	with connection.cursor(row_factory=dict_row) as cur:
		cur.execute(sql, params)
		return cur.fetchall()


def fetch_eligible_deadwood_datasets(connection: Connection, limit: int | None = None) -> list[dict]:
	sql = """
		with eligible as (
			select distinct
				p.dataset_id
			from v_export_polygon_candidates p
			join v2_datasets d on d.id = p.dataset_id
			join v2_metadata m on m.dataset_id = p.dataset_id
			where p.layer_type = 'deadwood'
				and p.deadwood_quality in ('great', 'sentinel_ok')
				and d.license = 'CC BY'
				and d.data_access = 'public'
				and d.aquisition_year is not null
				and d.aquisition_month is not null
				and d.aquisition_day is not null
				and (
					(m.metadata -> 'phenology' -> 'phenology_curve' ->> (
						extract(doy from make_date(d.aquisition_year, d.aquisition_month, d.aquisition_day))::int - 1
					))::int > 128
				)
		),
		doi_info as (
			select
				jt.dataset_id,
				string_agg(distinct dp.doi, '; ' order by dp.doi) as freidata_doi
			from jt_data_publication_datasets jt
			join data_publication dp on dp.id = jt.publication_id
			where dp.doi is not null
			group by jt.dataset_id
		),
		quality_info as (
			select
				dataset_id,
				min(deadwood_quality) as deadwood_quality
			from v_export_polygon_candidates
			where layer_type = 'deadwood'
			group by dataset_id
		)
		select
			d.id,
			d.file_name,
			d.authors,
			d.aquisition_year,
			d.aquisition_month,
			d.aquisition_day,
			d.additional_information,
			d.citation_doi,
			o.bbox::text as bbox,
			(m.metadata -> 'biome' ->> 'biome_name') as biome_name,
			q.deadwood_quality,
			d.license::text as license,
			d.platform::text as platform,
			di.freidata_doi
		from eligible e
		join v2_datasets d on d.id = e.dataset_id
		left join v2_orthos o on o.dataset_id = d.id
		left join v2_metadata m on m.dataset_id = d.id
		left join quality_info q on q.dataset_id = d.id
		left join doi_info di on di.dataset_id = d.id
		order by d.id
	"""
	params: tuple = ()
	if limit is not None:
		sql += "\nlimit %s"
		params = (limit,)

	with connection.cursor(row_factory=dict_row) as cur:
		cur.execute(sql, params)
		return cur.fetchall()
