from __future__ import annotations

import geopandas as gpd
import shapely


def keep_polygonal_geometries(geometries: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
	if geometries.empty:
		return geometries

	geometries = geometries.copy()
	geometries['geometry'] = shapely.make_valid(geometries.geometry.array)
	geometries = geometries.explode(index_parts=False)
	geometries = geometries[geometries.geometry.geom_type.isin(['Polygon', 'MultiPolygon'])].copy()
	return geometries[~geometries.geometry.is_empty].copy()


def clip_geometries_to_aoi(polygons: gpd.GeoDataFrame, aoi: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
	if polygons.empty or aoi.empty:
		return polygons

	polygons = polygons.copy()
	aoi = aoi.copy()
	polygons['geometry'] = shapely.make_valid(polygons.geometry.array)
	aoi_geom = shapely.make_valid(aoi.geometry.iloc[0])
	polygons['geometry'] = polygons.geometry.intersection(aoi_geom)
	return polygons[~polygons.geometry.is_empty].copy()
