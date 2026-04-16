from __future__ import annotations

from pathlib import Path

import rasterio
from rasterio.windows import transform as window_transform
from shapely.geometry import box

from .labels import LabelRepository
from .orthophotos import OrthophotoTileProvider, Tile


def select_aoi_covered_tiles(
	*,
	dataset_id: int,
	label_repository: LabelRepository,
	tile_provider: OrthophotoTileProvider,
	patch_size_px: int,
) -> list[Tile]:
	aoi = label_repository.get_aoi(dataset_id)
	with tile_provider.open_dataset(dataset_id) as src:
		aoi_in_source_crs = aoi.to_crs(src.crs) if src.crs is not None else aoi
		aoi_geometry = aoi_in_source_crs.geometry.union_all()
		return [
			tile
			for tile in tile_provider.iter_tiles(
				dataset_id=dataset_id,
				patch_size_px=patch_size_px,
				overlap_px=0,
			)
			if aoi_geometry.covers(box(*tile.bounds))
		]


def write_tile_geotiff(
	*,
	tile_provider: OrthophotoTileProvider,
	dataset_id: int,
	tile: Tile,
	output_path: Path,
	output_size_px: int,
) -> None:
	with tile_provider.open_dataset(dataset_id) as src:
		band_indexes = tuple(range(1, min(3, src.count) + 1))
		if not band_indexes:
			raise ValueError(f'No raster bands available for dataset {dataset_id}')

		if output_size_px is None:
			data = src.read(indexes=band_indexes, window=tile.window)
		else:
			data = src.read(
				indexes=band_indexes,
				window=tile.window,
				out_shape=(len(band_indexes), output_size_px, output_size_px),
				resampling=rasterio.enums.Resampling.bilinear,
			)
		if data.ndim == 2:
			data = data.reshape(1, data.shape[0], data.shape[1])

		profile = {
			'driver': 'GTiff',
			'height': int(data.shape[1]),
			'width': int(data.shape[2]),
			'count': int(data.shape[0]),
			'dtype': str(data.dtype),
			'crs': src.crs,
			'transform': window_transform(tile.window, src.transform),
			'compress': 'lzw',
		}
		with rasterio.open(output_path, 'w', **profile) as dst:
			dst.write(data)


def build_tile_row(*, dataset_id: int, tile: Tile, file_name: str) -> dict:
	minx, miny, maxx, maxy = tile.bounds
	return {
		'tile_id': f'{dataset_id}_{tile.row}_{tile.col}',
		'dataset_id': dataset_id,
		'row': tile.row,
		'col': tile.col,
		'file_name': file_name,
		'minx': minx,
		'miny': miny,
		'maxx': maxx,
		'maxy': maxy,
	}
