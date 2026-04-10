from __future__ import annotations

from pathlib import Path

import geopandas as gpd


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

	polygons.to_file(gpkg_path, layer=polygon_layer, driver='GPKG', index=False)
	aoi.to_file(gpkg_path, layer='aoi', driver='GPKG', index=False)
