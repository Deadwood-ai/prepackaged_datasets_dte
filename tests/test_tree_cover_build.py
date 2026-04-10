from contextlib import contextmanager
import json
import zipfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from deadtrees_prepackaged.config import BuildConfig
from deadtrees_prepackaged.datasets.standing_deadwood_aerial_global_conservative import (
	StandingDeadwoodAerialGlobalConservativeDefinition,
)
from deadtrees_prepackaged.datasets.tree_cover_aerial_global import TreeCoverAerialGlobalDefinition
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
			'authors': ['Zed', 'Alice'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': '10.1000/zeta',
			'freidata_doi': '10.1000/alpha; 10.1000/beta',
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'forest_cover_quality': 'great',
			'license': 'CC BY',
			'platform': 'aerial',
		}
	]

	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_aerial_global.connect_postgres',
		fake_connect_postgres,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_aerial_global.fetch_eligible_tree_cover_datasets',
		lambda _conn, limit=None: dataset_rows[:limit] if limit else dataset_rows,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_aerial_global.LabelRepository',
		FakeLabelRepository,
	)

	result = TreeCoverAerialGlobalDefinition().build(make_config(tmp_path))

	zip_path = result.artifact_paths['zip']
	assert zip_path.exists()
	assert result.output_dir == tmp_path / 'out'
	assert list(result.output_dir.iterdir()) == [zip_path]

	with zipfile.ZipFile(zip_path) as archive:
		names = sorted(archive.namelist())
		assert names == [
			'LICENSE.txt',
			'METADATA.csv',
			'METADATA.parquet',
			'manifest.json',
			'tree-cover-aerial-global_2026.04.09_test.gpkg',
		]
		license_text = archive.read('LICENSE.txt').decode('utf-8')
		assert license_text == (
			'License: CC BY 4.0\n'
			'License URL: https://creativecommons.org/licenses/by/4.0/\n'
			'\n'
			'Authors:\n'
			'Alice\n'
			'Zed\n'
			'\n'
			'Existing DOIs:\n'
			'10.1000/alpha\n'
			'10.1000/beta\n'
			'10.1000/zeta\n'
		)
		manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
		assert manifest['test_mode'] is True
		assert manifest['used_dataset_ids'] == [1]
		assert manifest['source_reference']['file'] == (
			'deadtrees_prepackaged/datasets/tree_cover_aerial_global.py'
		)
		assert 'package_version' in manifest['source_reference']


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
			'platform': 'aerial',
		}
	]

	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_aerial_global.connect_postgres',
		fake_connect_postgres,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_aerial_global.fetch_eligible_tree_cover_datasets',
		lambda _conn, limit=None: dataset_rows[:limit] if limit else dataset_rows,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.tree_cover_aerial_global.LabelRepository',
		FakeLabelRepository,
	)

	result = TreeCoverAerialGlobalDefinition().build(make_config(tmp_path))
	zip_path = result.artifact_paths['zip']
	extract_dir = tmp_path / 'unzipped'
	extract_dir.mkdir()

	with zipfile.ZipFile(zip_path) as archive:
		archive.extractall(extract_dir)

	gpkg_path = extract_dir / 'tree-cover-aerial-global_2026.04.09_test.gpkg'
	tree_cover = gpd.read_file(gpkg_path, layer='tree_cover')
	aoi = gpd.read_file(gpkg_path, layer='aoi')

	assert list(tree_cover.columns) == ['dataset_id', 'geometry']
	assert list(aoi.columns) == ['dataset_id', 'geometry']


def test_list_datasets_includes_deadwood_export():
	assert list_datasets() == ['standing-deadwood-aerial-global-conservative', 'tree-cover-aerial-global']


def test_deadwood_build_creates_expected_layer(monkeypatch, tmp_path):
	dataset_rows = [
		{
			'id': 1,
			'authors': ['Gamma', 'Beta'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': '10.1000/gamma',
			'freidata_doi': '10.1000/beta; 10.1000/alpha',
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'deadwood_quality': 'great',
			'license': 'CC BY',
			'platform': 'aerial',
		}
	]

	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.standing_deadwood_aerial_global_conservative.connect_postgres',
		fake_connect_postgres,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.standing_deadwood_aerial_global_conservative.fetch_eligible_deadwood_datasets',
		lambda _conn, limit=None: dataset_rows[:limit] if limit else dataset_rows,
	)
	monkeypatch.setattr(
		'deadtrees_prepackaged.datasets.standing_deadwood_aerial_global_conservative.LabelRepository',
		FakeLabelRepository,
	)

	result = StandingDeadwoodAerialGlobalConservativeDefinition().build(make_config(tmp_path))
	zip_path = result.artifact_paths['zip']
	extract_dir = tmp_path / 'deadwood_unzipped'
	extract_dir.mkdir()

	with zipfile.ZipFile(zip_path) as archive:
		archive.extractall(extract_dir)
		license_text = archive.read('LICENSE.txt').decode('utf-8')
		assert license_text == (
			'License: CC BY 4.0\n'
			'License URL: https://creativecommons.org/licenses/by/4.0/\n'
			'\n'
			'Authors:\n'
			'Beta\n'
			'Gamma\n'
			'\n'
			'Existing DOIs:\n'
			'10.1000/alpha\n'
			'10.1000/beta\n'
			'10.1000/gamma\n'
		)

	gpkg_path = extract_dir / 'standing-deadwood-aerial-global-conservative_2026.04.09_test.gpkg'
	deadwood = gpd.read_file(gpkg_path, layer='standing_deadwood')
	aoi = gpd.read_file(gpkg_path, layer='aoi')

	assert list(deadwood.columns) == ['dataset_id', 'geometry']
	assert list(aoi.columns) == ['dataset_id', 'geometry']
