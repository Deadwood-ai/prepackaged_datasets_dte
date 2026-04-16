from __future__ import annotations

import json
import logging
import shutil
import zipfile
from datetime import datetime, UTC
import pandas as pd

from ..config import BuildConfig
from ..helpers.geometry import clip_geometries_to_aoi, keep_polygonal_geometries
from ..helpers.geopackage import append_geopackage_layer
from ..helpers.labels import LabelRepository
from ..helpers.license import TREE_COVER_REFERENCE, build_license_text
from ..helpers.manifest import build_manifest
from ..helpers.metadata import build_dataset_metadata_row
from ..postgres.client import connect_postgres
from ..postgres.filters import public_cc_by_dataset_filters
from ..postgres.queries import fetch_dataset_rows
from ..result import BuildResult
from .base import DatasetDefinition


logger = logging.getLogger(__name__)


TREE_COVER_ELIGIBLE_DATASETS_SQL = """
	with eligible as (
		select distinct
			p.dataset_id
		from v_export_polygon_candidates p
		join v2_full_dataset_view fdv on fdv.id = p.dataset_id
		where p.layer_type = 'forest_cover'
			and p.forest_cover_quality in ('great', 'sentinel_ok')
			and {common_dataset_filters}
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
""".format(
	common_dataset_filters=public_cc_by_dataset_filters(
		dataset_alias='fdv',
		require_acquisition_date=True,
	),
)


def fetch_eligible_tree_cover_datasets(connection, limit: int | None = None) -> list[dict]:
	return fetch_dataset_rows(
		connection=connection,
		sql=TREE_COVER_ELIGIBLE_DATASETS_SQL,
		limit=limit,
		query_name='tree cover eligible dataset query',
	)


class TreeCoverAerialGlobalDefinition(DatasetDefinition):
	name = 'tree-cover-aerial-global'
	source_file = 'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
	user_description = (
		'Export of all tree cover polygons derived from aerial orthophotos.'
	)
	technical_description = (
		'Dataset-level eligibility is defined from audited entries in '
		'v2_full_dataset_view that are public, CC BY, not archived, and have a '
		'complete acquisition date. Polygon eligibility is then restricted to '
		'v_export_polygon_candidates rows with layer_type = forest_cover and '
		'forest_cover_quality in {great, sentinel_ok}. For each eligible dataset, '
		'tree-cover polygons are loaded, clipped to the dataset AOI, reduced to '
		'polygonal geometries only, and appended incrementally to a single '
		'GeoPackage tree_cover layer. Datasets that yield no remaining polygons '
		'after loading or AOI clipping are excluded from the final package. The '
		'output ZIP contains the GeoPackage, dataset-level metadata tables, a '
		'package manifest, and attribution/license text.'
	)

	def build(self, config: BuildConfig) -> BuildResult:
		version = config.version or datetime.now(UTC).strftime('%Y.%m.%d')
		package_name = f'{self.name}_{version}'
		if config.test_mode:
			package_name = f'{package_name}_test'

		work_dir = config.working_dir / package_name
		output_dir = config.output_root
		zip_path = output_dir / f'{package_name}.zip'
		gpkg_path = work_dir / f'{package_name}.gpkg'

		if zip_path.exists():
			if not config.overwrite_existing:
				raise FileExistsError(f'Output already exists: {zip_path}')
			zip_path.unlink()

		if work_dir.exists():
			shutil.rmtree(work_dir)
		work_dir.mkdir(parents=True, exist_ok=True)
		logger.info(
			"Starting dataset build: dataset=%s package=%s test_mode=%s",
			self.name,
			package_name,
			config.test_mode,
		)

		with connect_postgres(config) as conn:
			logger.info("Connected to PostgreSQL for dataset=%s", self.name)
			labels = LabelRepository(conn)
			dataset_rows = fetch_eligible_tree_cover_datasets(conn, limit=10 if config.test_mode else None)
			logger.info("Fetched %s eligible dataset rows for dataset=%s", len(dataset_rows), self.name)

			metadata_rows: list[dict] = []
			used_dataset_ids: list[int] = []
			tree_cover_feature_count = 0
			aoi_feature_count = 0

			for dataset_row in dataset_rows:
				dataset_id = int(dataset_row['id'])
				logger.info("Processing dataset_id=%s for dataset=%s", dataset_id, self.name)
				tree_cover = labels.get_tree_cover_geometries(dataset_id)
				logger.info(
					"Loaded %s tree cover geometries for dataset_id=%s",
					len(tree_cover),
					dataset_id,
				)
				if tree_cover.empty:
					logger.info("Skipping dataset_id=%s because no tree cover geometries were found", dataset_id)
					continue

				aoi = labels.get_aoi(dataset_id)
				logger.info("Loaded %s AOI geometries for dataset_id=%s", len(aoi), dataset_id)
				tree_cover = clip_geometries_to_aoi(tree_cover, aoi)
				tree_cover = keep_polygonal_geometries(tree_cover)
				logger.info(
					"After AOI clipping and polygon cleanup dataset_id=%s has %s tree cover geometries",
					dataset_id,
					len(tree_cover),
				)
				if tree_cover.empty:
					logger.info("Skipping dataset_id=%s because all geometries were removed after clipping", dataset_id)
					continue

				append_geopackage_layer(gpkg_path=gpkg_path, features=tree_cover, layer='tree_cover')
				append_geopackage_layer(gpkg_path=gpkg_path, features=aoi, layer='aoi')
				tree_cover_feature_count += int(len(tree_cover))
				aoi_feature_count += int(len(aoi))
				used_dataset_ids.append(dataset_id)
				metadata_rows.append(build_dataset_metadata_row(dataset_row))
				logger.info("Accepted dataset_id=%s for dataset=%s", dataset_id, self.name)

		if tree_cover_feature_count == 0 or aoi_feature_count == 0:
			raise ValueError('No eligible tree cover export data found.')
		logger.info(
			"Prepared %s datasets with %s tree cover features and %s metadata rows for dataset=%s",
			len(used_dataset_ids),
			tree_cover_feature_count,
			len(metadata_rows),
			self.name,
		)
		logger.info(
			"Wrote geopackage for dataset=%s path=%s features=%s",
			self.name,
			gpkg_path,
			tree_cover_feature_count,
		)

		metadata_csv = work_dir / 'METADATA.csv'
		metadata_parquet = work_dir / 'METADATA.parquet'
		license_path = work_dir / 'LICENSE.txt'
		metadata_df = pd.DataFrame(metadata_rows)
		metadata_df.to_csv(metadata_csv, index=False)
		metadata_df.to_parquet(metadata_parquet, index=False)
		license_path.write_text(
			build_license_text(dataset_rows, package_references=[TREE_COVER_REFERENCE]),
			encoding='utf-8',
		)
		logger.info("Wrote metadata and license files for dataset=%s", self.name)

		manifest = build_manifest(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			used_dataset_ids=used_dataset_ids,
			tree_cover_feature_count=tree_cover_feature_count,
			dataset_count=int(len(used_dataset_ids)),
			artifact_names=[
				gpkg_path.name,
				metadata_csv.name,
				metadata_parquet.name,
				license_path.name,
				'manifest.json',
			],
			test_mode=config.test_mode,
			source_file=self.source_file,
		)
		manifest_path = work_dir / 'manifest.json'
		manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
		logger.info("Wrote manifest for dataset=%s", self.name)

		output_dir.mkdir(parents=True, exist_ok=True)
		with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
			for path in sorted(work_dir.iterdir()):
				if not path.is_file():
					continue
				archive.write(path, arcname=path.name)
		logger.info("Created output zip for dataset=%s path=%s", self.name, zip_path)

		shutil.rmtree(work_dir)
		logger.info("Cleaned work directory for dataset=%s path=%s", self.name, work_dir)

		return BuildResult(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			output_dir=output_dir,
			artifact_paths={
				'zip': zip_path,
			},
			used_dataset_ids=used_dataset_ids,
			dataset_metadata_rows=metadata_rows,
		)
