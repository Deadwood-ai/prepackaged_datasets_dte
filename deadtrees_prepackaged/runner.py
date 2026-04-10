from __future__ import annotations

from .config import BuildConfig
from .result import BuildResult


_DATASET_NAMES = ['standing-deadwood-aerial-global-conservative', 'tree-cover-aerial-global']


def list_datasets() -> list[str]:
	return sorted(_DATASET_NAMES)


def build_dataset(name: str, config: BuildConfig) -> BuildResult:
	if name == 'tree-cover-aerial-global':
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
