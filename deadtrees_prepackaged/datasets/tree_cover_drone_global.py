from __future__ import annotations

import json
import shutil
from datetime import datetime, UTC
from pathlib import Path

import geopandas as gpd
import pandas as pd

from ..config import BuildConfig
from ..helpers.geopackage import write_tree_cover_package
from ..helpers.labels import LabelRepository
from ..helpers.manifest import build_manifest
from ..helpers.metadata import build_dataset_metadata_row
from ..result import BuildResult
from ..supabase.client import create_supabase_client
from ..supabase.queries import fetch_eligible_tree_cover_datasets
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

		work_dir = config.working_dir / package_name
		output_dir = config.output_root / self.name / version

		if output_dir.exists():
			if not config.overwrite_existing:
				raise FileExistsError(f'Output already exists: {output_dir}')
			shutil.rmtree(output_dir)

		if work_dir.exists():
			shutil.rmtree(work_dir)
		work_dir.mkdir(parents=True, exist_ok=True)

		client = create_supabase_client(config.supabase_url, config.supabase_key)
		labels = LabelRepository(client)
		dataset_rows = fetch_eligible_tree_cover_datasets(client)

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
		)
		manifest_path = work_dir / 'manifest.json'
		manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')

		output_dir.parent.mkdir(parents=True, exist_ok=True)
		shutil.move(str(work_dir), str(output_dir))

		return BuildResult(
			dataset_name=self.name,
			package_name=package_name,
			version=version,
			output_dir=output_dir,
			artifact_paths={
				'gpkg': output_dir / gpkg_path.name,
				'metadata_csv': output_dir / metadata_csv.name,
				'metadata_parquet': output_dir / metadata_parquet.name,
				'manifest': output_dir / manifest_path.name,
			},
			used_dataset_ids=used_dataset_ids,
			dataset_metadata_rows=metadata_rows,
		)
