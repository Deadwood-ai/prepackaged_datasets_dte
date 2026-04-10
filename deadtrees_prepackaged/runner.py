from __future__ import annotations

from .config import BuildConfig
from .result import BuildResult


_DATASET_NAMES = ['standing-deadwood-drone-global-conservative', 'tree-cover-drone-global']


def list_datasets() -> list[str]:
	return sorted(_DATASET_NAMES)


def build_dataset(name: str, config: BuildConfig) -> BuildResult:
	if name == 'tree-cover-drone-global':
		from .datasets.tree_cover_drone_global import TreeCoverDroneGlobalDefinition
		definition = TreeCoverDroneGlobalDefinition()
	elif name == 'standing-deadwood-drone-global-conservative':
		from .datasets.standing_deadwood_drone_global_conservative import (
			StandingDeadwoodDroneGlobalConservativeDefinition,
		)
		definition = StandingDeadwoodDroneGlobalConservativeDefinition()
	else:
		raise ValueError(f'Unknown dataset definition: {name}')

	return definition.build(config)
