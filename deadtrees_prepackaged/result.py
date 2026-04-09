from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class BuildResult:
	dataset_name: str
	package_name: str
	version: str
	output_dir: Path
	artifact_paths: dict[str, Path]
	used_dataset_ids: list[int]
	dataset_metadata_rows: list[dict[str, Any]]
