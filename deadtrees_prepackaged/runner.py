from __future__ import annotations

from .config import BuildConfig
from .result import BuildResult


_DATASET_NAMES = ['tree-cover-drone-global']


def list_datasets() -> list[str]:
	return sorted(_DATASET_NAMES)


def build_dataset(name: str, config: BuildConfig) -> BuildResult:
	if name != 'tree-cover-drone-global':
		raise ValueError(f'Unknown dataset definition: {name}')

	from .datasets.tree_cover_drone_global import TreeCoverDroneGlobalDefinition

	definition = TreeCoverDroneGlobalDefinition()

	return definition.build(config)
