from __future__ import annotations

from .config import BuildConfig
from .result import BuildResult


_DATASET_NAMES = [
	'image-tiles-1024-global-aerial-sampled-20-random',
	'standing-deadwood-aerial-global-conservative',
	'tree-cover-aerial-global',
]


def list_datasets() -> list[str]:
	return sorted(_DATASET_NAMES)


def build_dataset(name: str, config: BuildConfig) -> BuildResult:
	if name == 'image-tiles-1024-global-aerial-sampled-20-random':
		from .datasets.image_tiles_1024_global_aerial_sampled_20_random import (
			ImageTiles1024GlobalAerialSampled20RandomDefinition,
		)
		definition = ImageTiles1024GlobalAerialSampled20RandomDefinition()
	elif name == 'tree-cover-aerial-global':
		from .datasets.tree_cover_aerial_global import TreeCoverAerialGlobalDefinition
		definition = TreeCoverAerialGlobalDefinition()
	elif name == 'standing-deadwood-aerial-global-conservative':
		from .datasets.standing_deadwood_aerial_global_conservative import (
			StandingDeadwoodAerialGlobalConservativeDefinition,
		)
		definition = StandingDeadwoodAerialGlobalConservativeDefinition()
	else:
		raise ValueError(f'Unknown dataset definition: {name}')

	return definition.build(config)
