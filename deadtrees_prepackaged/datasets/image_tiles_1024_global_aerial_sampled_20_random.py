from __future__ import annotations

import json
import logging
import random
import shutil
import zipfile
from datetime import UTC, datetime

import pandas as pd

from ..config import BuildConfig
from ..helpers.license import IMAGE_TILE_SAMPLING_REFERENCE, build_license_text
from ..helpers.manifest import build_manifest
from ..helpers.metadata import build_dataset_metadata_row
from ..helpers.labels import LabelRepository
from ..helpers.orthophotos import OrthophotoTileProvider
from ..helpers.tiles import build_tile_row, select_aoi_covered_tiles, write_tile_geotiff
from ..postgres.client import connect_postgres
from ..postgres.filters import public_cc_by_dataset_filters
from ..postgres.queries import fetch_dataset_rows
from ..result import BuildResult
from .base import DatasetDefinition


logger = logging.getLogger(__name__)

TILE_SIZE_PX = 1024
MAX_RANDOM_TILES_PER_DATASET = 20

IMAGE_TILES_1024_GLOBAL_AERIAL_SAMPLED_20_RANDOM_SQL = """
	with doi_info as (
		select
			jt.dataset_id,
			string_agg(distinct dp.doi, '; ' order by dp.doi) as freidata_doi
		from jt_data_publication_datasets jt
		join data_publication dp on dp.id = jt.publication_id
		where dp.doi is not null
		group by jt.dataset_id
	)
	select
		fdv.id,
		fdv.file_name,
		fdv.authors,
		fdv.aquisition_year,
		fdv.aquisition_month,
		fdv.aquisition_day,
		fdv.additional_information,
		fdv.citation_doi,
		fdv.bbox::text as bbox,
		fdv.biome_name,
		fdv.license::text as license,
		fdv.platform::text as platform,
		coalesce(di.freidata_doi, fdv.freidata_doi) as freidata_doi,
		fdv.ortho_file_name
	from v2_full_dataset_view fdv
	left join doi_info di on di.dataset_id = fdv.id
	where {common_dataset_filters}
		and fdv.ortho_file_name is not null
		and exists (
			select 1
			from v2_aois a
			where a.dataset_id = fdv.id
		)
	order by fdv.id
""".format(
	common_dataset_filters=public_cc_by_dataset_filters(
		dataset_alias='fdv',
		require_acquisition_date=True,
	),
)


def fetch_eligible_image_tile_datasets(connection, limit: int | None = None) -> list[dict]:
	return fetch_dataset_rows(
		connection=connection,
		sql=IMAGE_TILES_1024_GLOBAL_AERIAL_SAMPLED_20_RANDOM_SQL,
		limit=limit,
		query_name='image tiles 1024 eligible dataset query',
	)


class ImageTiles1024GlobalAerialSampled20RandomDefinition(DatasetDefinition):
	name = 'image-tiles-1024-global-aerial-sampled-20-random'
	source_file = 'deadtrees_prepackaged/datasets/image_tiles_1024_global_aerial_sampled_20_random.py'
	user_description = (
		'Random sample of 1024x1024 orthophoto tiles from audited public datasets.'
	)
	technical_description = (
		'Dataset eligibility is defined directly from audited entries in '
		'v2_full_dataset_view that are public, CC BY, not archived, have a complete '
		'acquisition date, include an orthophoto file, and have at least one AOI. '
		'For each eligible orthophoto, the raster is partitioned into non-overlapping '
		'1024x1024 source windows, and only tiles whose full bounds are covered by '
		'the AOI are retained. A deterministic random sample seeded by dataset_id '
		'selects at most 20 tiles per dataset from those AOI-covered candidates. '
		'Selected tiles are written as GeoTIFF files under tiles/ in the original '
		'orthophoto CRS and native source resolution, and only the first three source '
		'bands (RGB) are read and saved. The package also includes dataset-level '
		'metadata tables, a per-tile index table, a package manifest, and '
		'attribution/license text inside the final ZIP archive.'
	)

	def build(self, config: BuildConfig) -> BuildResult:
		version = config.version or datetime.now(UTC).strftime('%Y.%m.%d')
		package_name = f'{self.name}_{version}'
		if config.test_mode:
			package_name = f'{package_name}_test'

		work_dir = config.working_dir / package_name
		output_dir = config.output_root
		zip_path = output_dir / f'{package_name}.zip'
		tiles_dir = work_dir / 'tiles'

		if zip_path.exists():
			if not config.overwrite_existing:
				raise FileExistsError(f'Output already exists: {zip_path}')
			zip_path.unlink()

		if work_dir.exists():
			shutil.rmtree(work_dir)
		tiles_dir.mkdir(parents=True, exist_ok=True)
		logger.info(
			"Starting dataset build: dataset=%s package=%s test_mode=%s",
			self.name,
			package_name,
			config.test_mode,
		)

		with connect_postgres(config) as conn:
			logger.info("Connected to PostgreSQL for dataset=%s", self.name)
			labels = LabelRepository(conn)
			tile_provider = OrthophotoTileProvider(conn, config.storage_root)
			dataset_rows = fetch_eligible_image_tile_datasets(conn, limit=10 if config.test_mode else None)
			logger.info("Fetched %s eligible dataset rows for dataset=%s", len(dataset_rows), self.name)

			metadata_rows: list[dict] = []
			tile_rows: list[dict] = []
			used_dataset_ids: list[int] = []

			for dataset_row in dataset_rows:
				dataset_id = int(dataset_row['id'])
				logger.info("Processing dataset_id=%s for dataset=%s", dataset_id, self.name)
				eligible_tiles = select_aoi_covered_tiles(
					dataset_id=dataset_id,
					label_repository=labels,
					tile_provider=tile_provider,
					patch_size_px=TILE_SIZE_PX,
				)
				logger.info(
					"Found %s AOI-covered candidate tiles for dataset_id=%s",
					len(eligible_tiles),
					dataset_id,
				)
				if not eligible_tiles:
					logger.info("Skipping dataset_id=%s because no eligible tiles were found", dataset_id)
					continue

				sampled_tiles = random.Random(dataset_id).sample(
					eligible_tiles,
					k=min(MAX_RANDOM_TILES_PER_DATASET, len(eligible_tiles)),
				)
				logger.info(
					"Selected %s random tiles for dataset_id=%s",
					len(sampled_tiles),
					dataset_id,
				)
				dataset_tiles_dir = tiles_dir / str(dataset_id)
				dataset_tiles_dir.mkdir(parents=True, exist_ok=True)
				for tile in sampled_tiles:
					file_name = f'dataset_{dataset_id}_r{tile.row:05d}_c{tile.col:05d}.tif'
					write_tile_geotiff(
						tile_provider=tile_provider,
						dataset_id=dataset_id,
						tile=tile,
						output_path=dataset_tiles_dir / file_name,
						output_size_px=TILE_SIZE_PX,
					)
					tile_rows.append(
						build_tile_row(
							dataset_id=dataset_id,
							tile=tile,
							file_name=f'{dataset_id}/{file_name}',
						)
					)

				used_dataset_ids.append(dataset_id)
				metadata_rows.append(build_dataset_metadata_row(dataset_row))

		if not tile_rows:
			raise ValueError('No eligible image tiles were exported.')

		metadata_csv = work_dir / 'METADATA.csv'
		metadata_parquet = work_dir / 'METADATA.parquet'
		tiles_csv = work_dir / 'TILES.csv'
		tiles_parquet = work_dir / 'TILES.parquet'
		license_path = work_dir / 'LICENSE.txt'
		pd.DataFrame(metadata_rows).to_csv(metadata_csv, index=False)
		pd.DataFrame(metadata_rows).to_parquet(metadata_parquet, index=False)
		pd.DataFrame(tile_rows).to_csv(tiles_csv, index=False)
		pd.DataFrame(tile_rows).to_parquet(tiles_parquet, index=False)
		license_path.write_text(
			build_license_text(
				dataset_rows,
				package_references=[IMAGE_TILE_SAMPLING_REFERENCE],
			),
			encoding='utf-8',
		)
		logger.info("Wrote metadata, tile index, and license files for dataset=%s", self.name)

		manifest = build_manifest(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			used_dataset_ids=used_dataset_ids,
			tree_cover_feature_count=len(tile_rows),
			dataset_count=int(len(used_dataset_ids)),
			artifact_names=[
				'tiles/',
				metadata_csv.name,
				metadata_parquet.name,
				tiles_csv.name,
				tiles_parquet.name,
				license_path.name,
				'manifest.json',
			],
			test_mode=config.test_mode,
			source_file=self.source_file,
			feature_count_field='tile_count',
		)
		manifest_path = work_dir / 'manifest.json'
		manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
		logger.info("Wrote manifest for dataset=%s", self.name)

		output_dir.mkdir(parents=True, exist_ok=True)
		with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
			for path in sorted(work_dir.rglob('*')):
				if not path.is_file():
					continue
				archive.write(path, arcname=str(path.relative_to(work_dir)))
		logger.info("Created output zip for dataset=%s path=%s", self.name, zip_path)

		shutil.rmtree(work_dir)
		logger.info("Cleaned work directory for dataset=%s path=%s", self.name, work_dir)

		return BuildResult(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			output_dir=output_dir,
			artifact_paths={'zip': zip_path},
			used_dataset_ids=used_dataset_ids,
			dataset_metadata_rows=metadata_rows,
		)
