from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from psycopg import Connection
from psycopg.rows import dict_row
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window


@dataclass(slots=True)
class Tile:
	dataset_id: int
	window: Window
	row: int
	col: int
	bounds: tuple[float, float, float, float]


class OrthophotoTileProvider:
	def __init__(self, connection: Connection, storage_root: Path | str):
		self.connection = connection
		self.storage_root = Path(storage_root)

	def get_ortho_path(self, dataset_id: int) -> Path:
		with self.connection.cursor(row_factory=dict_row) as cur:
			cur.execute(
				"""
				select ortho_file_name
				from v2_orthos
				where dataset_id = %s
				limit 1
				""",
				(dataset_id,),
			)
			rows = cur.fetchall()
		if not rows:
			raise ValueError(f'No orthophoto found for dataset {dataset_id}')

		return self.storage_root / 'archive' / rows[0]['ortho_file_name']

	def open_dataset(self, dataset_id: int):
		return rasterio.open(self.get_ortho_path(dataset_id))

	def iter_tiles(
		self,
		dataset_id: int,
		patch_size_px: int,
		resolution_cm: float | None = None,
		overlap_px: int = 0,
	) -> Iterator[Tile]:
		with self.open_dataset(dataset_id) as src:
			native_resolution_cm = abs(src.transform.a) * 100
			target_resolution_cm = resolution_cm or native_resolution_cm
			scale = target_resolution_cm / native_resolution_cm
			source_patch_size_px = max(1, int(round(patch_size_px * scale)))
			source_overlap_px = max(0, int(round(overlap_px * scale)))
			step = max(1, source_patch_size_px - source_overlap_px)

			row_index = 0
			for row_off in range(0, src.height - source_patch_size_px + 1, step):
				col_index = 0
				for col_off in range(0, src.width - source_patch_size_px + 1, step):
					window = Window(col_off=col_off, row_off=row_off, width=source_patch_size_px, height=source_patch_size_px)
					bounds = rasterio.windows.bounds(window, src.transform)
					yield Tile(
						dataset_id=dataset_id,
						window=window,
						row=row_index,
						col=col_index,
						bounds=bounds,
					)
					col_index += 1
				row_index += 1

	def read_tile(
		self,
		dataset_id: int,
		tile: Tile,
		out_size_px: int | None = None,
	):
		with self.open_dataset(dataset_id) as src:
			if out_size_px is None:
				return src.read(window=tile.window)

			return src.read(
				window=tile.window,
				out_shape=(src.count, out_size_px, out_size_px),
				resampling=Resampling.bilinear,
			)
