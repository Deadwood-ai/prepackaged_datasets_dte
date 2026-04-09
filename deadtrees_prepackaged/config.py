from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class BuildConfig:
	supabase_url: str
	supabase_key: str
	storage_root: Path | str
	output_root: Path | str
	working_dir: Path | str
	version: str | None = None
	test_mode: bool = False
	overwrite_existing: bool = False
	keep_workdir: bool = False

	def __post_init__(self) -> None:
		self.storage_root = Path(self.storage_root)
		self.output_root = Path(self.output_root)
		self.working_dir = Path(self.working_dir)
