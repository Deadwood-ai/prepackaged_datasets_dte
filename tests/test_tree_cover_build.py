from contextlib import contextmanager
import json
import zipfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from deadtrees_prepackaged.config import BuildConfig
from deadtrees_prepackaged.datasets.standing_deadwood_drone_global_conservative import (
	StandingDeadwoodDroneGlobalConservativeDefinition,
)
from deadtrees_prepackaged.datasets.tree_cover_drone_global import TreeCoverDroneGlobalDefinition
from deadtrees_prepackaged.runner import list_datasets


class FakeConnection:
	pass


class FakeLabelRepository:
	def __init__(self, _connection):
		pass

	def get_deadwood_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
		return self.get_tree_cover_geometries(dataset_id)

	def get_tree_cover_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
		return gpd.GeoDataFrame(
			[{'dataset_id': dataset_id, 'geometry': Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])}],
			geometry='geometry',
			crs='EPSG:4326',
		)

	def get_aoi(self, dataset_id: int) -> gpd.GeoDataFrame:
		return gpd.GeoDataFrame(
			[{'dataset_id': dataset_id, 'geometry': Polygon([(-1, -1), (2, -1), (2, 2), (-1, 2)])}],
			geometry='geometry',
			crs='EPSG:4326',
		)


@contextmanager
def fake_connect_postgres(_config):
	yield FakeConnection()


def make_config(tmp_path: Path) -> BuildConfig:
	return BuildConfig(
		pg_dsn='postgresql://user:pw@host:5432/db',
		pg_host=None,
		pg_port=None,
		pg_database=None,
		pg_user=None,
		pg_password=None,
		pg_sslmode=None,
		storage_root=tmp_path / 'storage',
		output_root=tmp_path / 'out',
		working_dir=tmp_path / 'work',
		version='2026.04.09',
		test_mode=True,
	)


def test_build_creates_single_zip_and_cleans_intermediate_files(monkeypatch, tmp_path):
	dataset_rows = [
		{
			'id': 1,
			'authors': ['Author'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': None,
			'freidata_doi': None,
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'forest_cover_quality': 'great',
			'license': 'CC BY',
			'platform': 'drone',
		}
	]

	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_drone_global.connect_postgres',
		fake_connect_postgres,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_drone_global.fetch_eligible_tree_cover_datasets',
		lambda _conn, limit=None: dataset_rows[:limit] if limit else dataset_rows,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_drone_global.LabelRepository',
		FakeLabelRepository,
	)

	result = TreeCoverDroneGlobalDefinition().build(make_config(tmp_path))

	zip_path = result.artifact_paths['zip']
	assert zip_path.exists()
	assert result.output_dir == tmp_path / 'out'
	assert list(result.output_dir.iterdir()) == [zip_path]

	with zipfile.ZipFile(zip_path) as archive:
		names = sorted(archive.namelist())
		assert names == [
			'METADATA.csv',
			'METADATA.parquet',
			'manifest.json',
			'tree-cover-drone-global_2026.04.09_test.gpkg',
		]
		manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
		assert manifest['test_mode'] is True
		assert manifest['used_dataset_ids'] == [1]


def test_build_geopackage_layers_have_expected_columns(monkeypatch, tmp_path):
	dataset_rows = [
		{
			'id': 1,
			'authors': ['Author'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': None,
			'freidata_doi': None,
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'forest_cover_quality': 'great',
			'license': 'CC BY',
			'platform': 'drone',
		}
	]

	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_drone_global.connect_postgres',
		fake_connect_postgres,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_drone_global.fetch_eligible_tree_cover_datasets',
		lambda _conn, limit=None: dataset_rows[:limit] if limit else dataset_rows,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_drone_global.LabelRepository',
		FakeLabelRepository,
	)

	result = TreeCoverDroneGlobalDefinition().build(make_config(tmp_path))
	zip_path = result.artifact_paths['zip']
	extract_dir = tmp_path / 'unzipped'
	extract_dir.mkdir()

	with zipfile.ZipFile(zip_path) as archive:
		archive.extractall(extract_dir)

	gpkg_path = extract_dir / 'tree-cover-drone-global_2026.04.09_test.gpkg'
	tree_cover = gpd.read_file(gpkg_path, layer='tree_cover')
	aoi = gpd.read_file(gpkg_path, layer='aoi')

	assert list(tree_cover.columns) == ['dataset_id', 'geometry']
	assert list(aoi.columns) == ['dataset_id', 'geometry']


def test_list_datasets_includes_deadwood_export():
	assert list_datasets() == ['standing-deadwood-drone-global-conservative', 'tree-cover-drone-global']


def test_deadwood_build_creates_expected_layer(monkeypatch, tmp_path):
	dataset_rows = [
		{
			'id': 1,
			'authors': ['Author'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': None,
			'freidata_doi': None,
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'deadwood_quality': 'great',
			'license': 'CC BY',
			'platform': 'drone',
		}
	]

	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.standing_deadwood_drone_global_conservative.connect_postgres',
		fake_connect_postgres,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.standing_deadwood_drone_global_conservative.fetch_eligible_deadwood_datasets',
		lambda _conn, limit=None: dataset_rows[:limit] if limit else dataset_rows,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.standing_deadwood_drone_global_conservative.LabelRepository',
		FakeLabelRepository,
	)

	result = StandingDeadwoodDroneGlobalConservativeDefinition().build(make_config(tmp_path))
	zip_path = result.artifact_paths['zip']
	extract_dir = tmp_path / 'deadwood_unzipped'
	extract_dir.mkdir()

	with zipfile.ZipFile(zip_path) as archive:
		archive.extractall(extract_dir)

	gpkg_path = extract_dir / 'standing-deadwood-drone-global-conservative_2026.04.09_test.gpkg'
	deadwood = gpd.read_file(gpkg_path, layer='standing_deadwood')
	aoi = gpd.read_file(gpkg_path, layer='aoi')

	assert list(deadwood.columns) == ['dataset_id', 'geometry']
	assert list(aoi.columns) == ['dataset_id', 'geometry']
