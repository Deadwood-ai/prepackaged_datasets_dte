from __future__ import annotations

from pathlib import Path

import geopandas as gpd


def append_geopackage_layer(
	gpkg_path: Path,
	features: gpd.GeoDataFrame,
	layer: str,
) -> None:
	if features.empty:
		raise ValueError(f'No features to write for layer {layer}.')

	write_kwargs = {
		'layer': layer,
		'driver': 'GPKG',
		'index': False,
	}
	if gpkg_path.exists():
		write_kwargs['mode'] = 'a'

	features.to_file(gpkg_path, **write_kwargs)


def write_tree_cover_package(gpkg_path: Path, tree_cover: gpd.GeoDataFrame, aoi: gpd.GeoDataFrame) -> None:
	write_polygon_package(gpkg_path=gpkg_path, polygons=tree_cover, aoi=aoi, polygon_layer='tree_cover')


def write_polygon_package(
	gpkg_path: Path,
	polygons: gpd.GeoDataFrame,
	aoi: gpd.GeoDataFrame,
	polygon_layer: str,
) -> None:
	if polygons.empty:
		raise ValueError('No polygon features to write.')
	if aoi.empty:
		raise ValueError('No AOI features to write.')

	append_geopackage_layer(gpkg_path=gpkg_path, features=polygons, layer=polygon_layer)
	append_geopackage_layer(gpkg_path=gpkg_path, features=aoi, layer='aoi')
