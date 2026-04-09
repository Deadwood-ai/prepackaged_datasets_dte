from __future__ import annotations

from pathlib import Path

import geopandas as gpd


def write_tree_cover_package(gpkg_path: Path, tree_cover: gpd.GeoDataFrame, aoi: gpd.GeoDataFrame) -> None:
	if tree_cover.empty:
		raise ValueError('No tree cover features to write.')
	if aoi.empty:
		raise ValueError('No AOI features to write.')

	tree_cover.to_file(gpkg_path, layer='tree_cover', driver='GPKG')
	aoi.to_file(gpkg_path, layer='aoi', driver='GPKG')
