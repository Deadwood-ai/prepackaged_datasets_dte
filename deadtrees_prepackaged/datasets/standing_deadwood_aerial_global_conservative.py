from __future__ import annotations

import json
import shutil
import zipfile
from datetime import UTC, datetime

import geopandas as gpd
import pandas as pd

from ..config import BuildConfig
from ..helpers.geometry import clip_geometries_to_aoi
from ..helpers.geopackage import write_polygon_package
from ..helpers.labels import LabelRepository
from ..helpers.manifest import build_manifest
from ..helpers.metadata import build_dataset_metadata_row
from ..postgres.client import connect_postgres
from ..postgres.queries import fetch_dataset_rows
from ..result import BuildResult
from .base import DatasetDefinition


STANDING_DEADWOOD_AERIAL_GLOBAL_CONSERVATIVE_SQL = """
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


def fetch_eligible_deadwood_datasets(connection, limit: int | None = None) -> list[dict]:
		return fetch_dataset_rows(
		connection=connection,
		sql=STANDING_DEADWOOD_AERIAL_GLOBAL_CONSERVATIVE_SQL,
		limit=limit,
	)


class StandingDeadwoodAerialGlobalConservativeDefinition(DatasetDefinition):
	name = 'standing-deadwood-aerial-global-conservative'
	user_description = (
		'Conservative export of standing deadwood cover polygons derived from orthophotos.'
	)
	technical_description = (
		'Standing deadwood polygons clipped to the AOI of public CC-BY datasets '
		'where deadwood quality is great or sentinel_ok and the phenology indicator '
		'at acquisition time is > 128.'
	)

	def build(self, config: BuildConfig) -> BuildResult:
		version = config.version or datetime.now(UTC).strftime('%Y.%m.%d')
		package_name = f'{self.name}_{version}'
		if config.test_mode:
			package_name = f'{package_name}_test'

		work_dir = config.working_dir / package_name
		output_dir = config.output_root
		zip_path = output_dir / f'{package_name}.zip'

		if zip_path.exists():
			if not config.overwrite_existing:
				raise FileExistsError(f'Output already exists: {zip_path}')
			zip_path.unlink()

		if work_dir.exists():
			shutil.rmtree(work_dir)
		work_dir.mkdir(parents=True, exist_ok=True)

		with connect_postgres(config) as conn:
			labels = LabelRepository(conn)
			dataset_rows = fetch_eligible_deadwood_datasets(conn, limit=10 if config.test_mode else None)

			deadwood_frames: list[gpd.GeoDataFrame] = []
			aoi_frames: list[gpd.GeoDataFrame] = []
			metadata_rows: list[dict] = []
			used_dataset_ids: list[int] = []

			for dataset_row in dataset_rows:
				dataset_id = int(dataset_row['id'])
				deadwood = labels.get_deadwood_geometries(dataset_id)
				if deadwood.empty:
					continue

				aoi = labels.get_aoi(dataset_id)
				deadwood = clip_geometries_to_aoi(deadwood, aoi)
				if deadwood.empty:
					continue

				deadwood_frames.append(deadwood)
				aoi_frames.append(aoi)
				used_dataset_ids.append(dataset_id)
				metadata_rows.append(build_dataset_metadata_row(dataset_row))

		if not deadwood_frames or not aoi_frames:
			raise ValueError('No eligible deadwood export data found.')

		deadwood_gdf = gpd.GeoDataFrame(
			pd.concat(deadwood_frames, ignore_index=True),
			geometry='geometry',
			crs='EPSG:4326',
		)
		aoi_gdf = gpd.GeoDataFrame(
			pd.concat(aoi_frames, ignore_index=True),
			geometry='geometry',
			crs='EPSG:4326',
		)

		gpkg_path = work_dir / f'{package_name}.gpkg'
		write_polygon_package(
			gpkg_path=gpkg_path,
			polygons=deadwood_gdf,
			aoi=aoi_gdf,
			polygon_layer='standing_deadwood',
		)

		metadata_csv = work_dir / 'METADATA.csv'
		metadata_parquet = work_dir / 'METADATA.parquet'
		metadata_df = pd.DataFrame(metadata_rows)
		metadata_df.to_csv(metadata_csv, index=False)
		metadata_df.to_parquet(metadata_parquet, index=False)

		manifest = build_manifest(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			used_dataset_ids=used_dataset_ids,
			tree_cover_feature_count=int(len(deadwood_gdf)),
			dataset_count=int(len(used_dataset_ids)),
			artifact_names=[gpkg_path.name, metadata_csv.name, metadata_parquet.name, 'manifest.json'],
			test_mode=config.test_mode,
		)
		manifest_path = work_dir / 'manifest.json'
		manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

		output_dir.mkdir(parents=True, exist_ok=True)
		with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
			for path in sorted(work_dir.iterdir()):
				if not path.is_file():
					continue
				archive.write(path, arcname=path.name)

		shutil.rmtree(work_dir)

		return BuildResult(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			output_dir=output_dir,
			artifact_paths={'zip': zip_path},
			used_dataset_ids=used_dataset_ids,
			dataset_metadata_rows=metadata_rows,
		)
