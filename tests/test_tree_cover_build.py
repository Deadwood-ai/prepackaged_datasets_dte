from contextlib import contextmanager
import json
import zipfile
from pathlib import Path

import geopandas as gpd
import fiona
import shapely
from shapely.geometry import GeometryCollection, Polygon

from deadtrees_prepackaged.config import BuildConfig
from deadtrees_prepackaged.datasets.standing_deadwood_aerial_global_conservative import (
	StandingDeadwoodAerialGlobalConservativeDefinition,
)
from deadtrees_prepackaged.datasets.tree_cover_aerial_global import TreeCoverAerialGlobalDefinition
from deadtrees_prepackaged.helpers.geometry import keep_polygonal_geometries
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
		assert 'Alice, Zed' in license_text
		assert 'https://deadtrees.earth, 10.1000/alpha, 10.1000/beta, 10.1000/zeta' in license_text
		assert 'OAM-TCD: A globally diverse dataset of high-resolution tree cover maps.' in license_text
		assert 'Creative Commons Attribution 4.0 International Public License' in license_text
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


def test_build_appends_multiple_datasets_to_single_layers(monkeypatch, tmp_path):
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
		},
		{
			'id': 2,
			'authors': ['Author'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 3,
			'additional_information': None,
			'citation_doi': None,
			'freidata_doi': None,
			'bbox': 'BOX(2 2,3 3)',
			'biome_name': 'Biome',
			'forest_cover_quality': 'great',
			'license': 'CC BY',
			'platform': 'aerial',
		},
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
	extract_dir = tmp_path / 'multi_dataset_unzipped'
	extract_dir.mkdir()

	with zipfile.ZipFile(zip_path) as archive:
		archive.extractall(extract_dir)

	gpkg_path = extract_dir / 'tree-cover-aerial-global_2026.04.09_test.gpkg'
	tree_cover = gpd.read_file(gpkg_path, layer='tree_cover').sort_values('dataset_id').reset_index(drop=True)
	aoi = gpd.read_file(gpkg_path, layer='aoi').sort_values('dataset_id').reset_index(drop=True)

	assert tree_cover['dataset_id'].tolist() == [1, 2]
	assert aoi['dataset_id'].tolist() == [1, 2]


def test_list_datasets_includes_deadwood_export():
	assert list_datasets() == ['standing-deadwood-aerial-global-conservative', 'tree-cover-aerial-global']


def test_keep_polygonal_geometries_drops_non_area_parts():
	geometries = gpd.GeoDataFrame(
		[
			{
				'dataset_id': 1,
				'geometry': GeometryCollection(
					[
						Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
						shapely.LineString([(0, 0), (2, 0)]),
					]
				),
			},
			{
				'dataset_id': 2,
				'geometry': GeometryCollection(
					[
						shapely.LineString([(0, 0), (1, 0)]),
					]
				),
			},
		],
		geometry='geometry',
		crs='EPSG:4326',
	)

	cleaned = keep_polygonal_geometries(geometries)

	assert len(cleaned) == 1
	assert cleaned.iloc[0]['dataset_id'] == 1
	assert cleaned.geometry.iloc[0].geom_type == 'Polygon'


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
			'phenology_curve': '[200]',
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
		assert 'Beta, Gamma' in license_text
		assert 'https://deadtrees.earth, 10.1000/alpha, 10.1000/beta, 10.1000/gamma' in license_text
		assert '10.1016/j.ophoto.2025.100104' in license_text
		assert 'Global, multi-scale standing deadwood segmentation in centimeter-scale aerial images.' in license_text
		assert 'Creative Commons Attribution 4.0 International Public License' in license_text

	gpkg_path = extract_dir / 'standing-deadwood-aerial-global-conservative_2026.04.09_test.gpkg'
	deadwood = gpd.read_file(gpkg_path, layer='standing_deadwood')
	aoi = gpd.read_file(gpkg_path, layer='aoi')

	assert list(deadwood.columns) == ['dataset_id', 'geometry']
	assert list(aoi.columns) == ['dataset_id', 'geometry']


def test_deadwood_build_keeps_zero_polygon_dataset_metadata_and_aoi(monkeypatch, tmp_path):
	dataset_rows = [
		{
			'id': 1,
			'authors': ['Gamma'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': None,
			'freidata_doi': None,
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'phenology_curve': '[200]',
			'deadwood_quality': 'great',
			'license': 'CC BY',
			'platform': 'aerial',
		},
		{
			'id': 2,
			'authors': ['Beta'],
			'aquisition_year': 2024,
			'aquisition_month': 1,
			'aquisition_day': 2,
			'additional_information': None,
			'citation_doi': None,
			'freidata_doi': None,
			'bbox': 'BOX(0 0,1 1)',
			'biome_name': 'Biome',
			'phenology_curve': '[200]',
			'deadwood_quality': 'great',
			'license': 'CC BY',
			'platform': 'aerial',
		},
	]

	class ZeroAfterClipLabelRepository(FakeLabelRepository):
		def get_deadwood_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
			if dataset_id == 1:
				return gpd.GeoDataFrame(
					[{'dataset_id': dataset_id, 'geometry': Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])}],
					geometry='geometry',
					crs='EPSG:4326',
				)
			return gpd.GeoDataFrame(
				[{'dataset_id': dataset_id, 'geometry': Polygon([(10, 10), (11, 10), (11, 11), (10, 11)])}],
				geometry='geometry',
				crs='EPSG:4326',
			)

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
		ZeroAfterClipLabelRepository,
	)

	result = StandingDeadwoodAerialGlobalConservativeDefinition().build(make_config(tmp_path))
	assert result.used_dataset_ids == [1, 2]
	assert len(result.dataset_metadata_rows) == 2

	zip_path = result.artifact_paths['zip']
	extract_dir = tmp_path / 'deadwood_zero_unzipped'
	extract_dir.mkdir()

	with zipfile.ZipFile(zip_path) as archive:
		archive.extractall(extract_dir)
		manifest = json.loads(archive.read('manifest.json').decode('utf-8'))
		assert manifest['used_dataset_ids'] == [1, 2]
		assert manifest['dataset_count'] == 2

	gpkg_path = extract_dir / 'standing-deadwood-aerial-global-conservative_2026.04.09_test.gpkg'
	deadwood = gpd.read_file(gpkg_path, layer='standing_deadwood')
	aoi = gpd.read_file(gpkg_path, layer='aoi')
	metadata = gpd.pd.read_csv(extract_dir / 'METADATA.csv')

	assert list(deadwood['dataset_id']) == [1]
	assert sorted(aoi['dataset_id'].tolist()) == [1, 2]
	assert sorted(metadata['dataset_id'].tolist()) == [1, 2]

def test_exports_write_polygon_only_layers(monkeypatch, tmp_path):
	class MixedGeometryLabelRepository(FakeLabelRepository):
		def get_deadwood_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
			return gpd.GeoDataFrame(
				[
					{
						'dataset_id': dataset_id,
						'geometry': GeometryCollection(
							[
								Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
								shapely.LineString([(0, 0), (2, 0)]),
							]
						),
					}
				],
				geometry='geometry',
				crs='EPSG:4326',
			)

		def get_tree_cover_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
			return self.get_deadwood_geometries(dataset_id)

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
			'phenology_curve': '[200]',
			'deadwood_quality': 'great',
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
		MixedGeometryLabelRepository,
	)
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
		MixedGeometryLabelRepository,
	)

	tree_result = TreeCoverAerialGlobalDefinition().build(make_config(tmp_path / 'tree'))
	deadwood_result = StandingDeadwoodAerialGlobalConservativeDefinition().build(make_config(tmp_path / 'deadwood'))

	for zip_path, layer_name in [
		(tree_result.artifact_paths['zip'], 'tree_cover'),
		(deadwood_result.artifact_paths['zip'], 'standing_deadwood'),
	]:
		extract_dir = tmp_path / f'extract_{layer_name}'
		extract_dir.mkdir()
		with zipfile.ZipFile(zip_path) as archive:
			archive.extractall(extract_dir)
		gpkg_path = next(extract_dir.glob('*.gpkg'))
		layer = gpd.read_file(gpkg_path, layer=layer_name)
		assert set(layer.geometry.geom_type.unique()) == {'Polygon'}
		assert set(fiona.listlayers(gpkg_path)) == {layer_name, 'aoi'}
