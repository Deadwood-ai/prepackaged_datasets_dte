from __future__ import annotations

import geopandas as gpd
from psycopg import Connection
from psycopg.rows import dict_row
from shapely import wkb


def _to_geodataframe(rows: list[dict]) -> gpd.GeoDataFrame:
	if not rows:
		return gpd.GeoDataFrame(geometry=[], crs='EPSG:4326')

	records = []
	for row in rows:
		record = dict(row)
		record['geometry'] = wkb.loads(record.pop('geometry_wkb'))
		records.append(record)

	return gpd.GeoDataFrame(records, geometry='geometry', crs='EPSG:4326')


class LabelRepository:
	def __init__(self, connection: Connection):
		self.connection = connection

	def get_tree_cover_geometries(self, dataset_id: int) -> gpd.GeoDataFrame:
		with self.connection.cursor(row_factory=dict_row) as cur:
			cur.execute(
				"""
				select
					dataset_id,
					ST_AsBinary(geometry) as geometry_wkb
				from v_export_polygon_candidates
				where dataset_id = %s
					and layer_type = 'forest_cover'
				order by id
				""",
				(dataset_id,),
			)
			return _to_geodataframe(cur.fetchall())

	def get_aoi(self, dataset_id: int) -> gpd.GeoDataFrame:
		with self.connection.cursor(row_factory=dict_row) as cur:
			cur.execute(
				"""
				select
					dataset_id,
					ST_AsBinary(ST_GeomFromGeoJSON(geometry::text)) as geometry_wkb
				from v2_aois
				where dataset_id = %s
				limit 1
				""",
				(dataset_id,),
			)
			rows = cur.fetchall()
		if not rows:
			raise ValueError(f'No AOI found for dataset {dataset_id}')

		aoi = _to_geodataframe([rows[0]])
		return aoi
