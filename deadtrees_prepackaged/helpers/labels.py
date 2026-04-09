from __future__ import annotations

import geopandas as gpd
from shapely.geometry import shape
from supabase import Client


def _to_geodataframe(rows: list[dict]) -> gpd.GeoDataFrame:
	if not rows:
		return gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')

	records = []
	for row in rows:
		record = dict(row)
		record['geometry'] = shape(record['geometry'])
		records.append(record)

	return gpd.GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')


class LabelRepository:
	def __init__(self, client: Client):
		self.client = client

	def get_tree_cover_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
		response = (
			self.client.table('v_export_polygon_candidates')
			.select('id, dataset_id, label_id, area_m2, properties, geometry')
			.eq('dataset_id', dataset_id)
			.eq('layer_type', 'forest_cover')
			.execute()
		)
		return _to_geodataframe(response.data or [])

	def get_aoi(self, dataset_id: int) -> gpd.GeoDataFrame:
		response = (
			self.client.table('v2_aois')
			.select('dataset_id, image_quality, notes, geometry')
			.eq('dataset_id', dataset_id)
			.execute()
		)
		rows = response.data or []
		if not rows:
			raise ValueError(f'No AOI found for dataset {dataset_id}')

		aoi = _to_geodataframe([rows[0]])
		return aoi
