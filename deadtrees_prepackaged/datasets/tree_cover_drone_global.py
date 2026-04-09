from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, UTC

import geopandas as gpd
import pandas as pd

from ..config import BuildConfig
from ..helpers.geopackage import write_tree_cover_package
from ..helpers.labels import LabelRepository
from ..helpers.manifest import build_manifest
from ..helpers.metadata import build_dataset_metadata_row
from ..postgres.client import connect_postgres
from ..postgres.queries import fetch_eligible_tree_cover_datasets
from ..result import BuildResult
from .base import DatasetDefinition


class TreeCoverDroneGlobalDefinition(DatasetDefinition):
	name = 'tree-cover-drone-global'
	user_description = (
		'Export of all tree cover polygons derived from drone orthophotos.'
	)
	technical_description = (
		'All tree cover polygons clipped to the AOI of audited public CC-BY datasets '
		'where forest cover quality is great or sentinel_ok.'
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
			dataset_rows = fetch_eligible_tree_cover_datasets(conn, limit=10 if config.test_mode else None)

			tree_cover_frames: list[gpd.GeoDataFrame] = []
			aoi_frames: list[gpd.GeoDataFrame] = []
			metadata_rows: list[dict] = []
			used_dataset_ids: list[int] = []

			for dataset_row in dataset_rows:
				dataset_id = int(dataset_row['id'])
				tree_cover = labels.get_tree_cover_geometries(dataset_id)
				if tree_cover.empty:
					continue

				aoi = labels.get_aoi(dataset_id)
				tree_cover['geometry'] = tree_cover.geometry.intersection(aoi.geometry.iloc[0])
				tree_cover = tree_cover[~tree_cover.geometry.is_empty].copy()
				if tree_cover.empty:
					continue

				tree_cover_frames.append(tree_cover)
				aoi_frames.append(aoi)
				used_dataset_ids.append(dataset_id)
				metadata_rows.append(build_dataset_metadata_row(dataset_row))

		if not tree_cover_frames or not aoi_frames:
			raise ValueError('No eligible tree cover export data found.')

		tree_cover_gdf = gpd.GeoDataFrame(
			pd.concat(tree_cover_frames, ignore_index=True),
			geometry='geometry',
			crs='EPSG:4326',
		)
		aoi_gdf = gpd.GeoDataFrame(
			pd.concat(aoi_frames, ignore_index=True),
			geometry='geometry',
			crs='EPSG:4326',
		)

		gpkg_path = work_dir / f'{package_name}.gpkg'
		write_tree_cover_package(gpkg_path=gpkg_path, tree_cover=tree_cover_gdf, aoi=aoi_gdf)

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
			tree_cover_feature_count=int(len(tree_cover_gdf)),
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
			artifact_paths={
				'zip': zip_path,
			},
			used_dataset_ids=used_dataset_ids,
			dataset_metadata_rows=metadata_rows,
		)
