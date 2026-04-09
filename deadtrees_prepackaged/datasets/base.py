from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import BuildConfig
from ..result import BuildResult


class DatasetDefinition(ABC):
	name: str
	user_description: str
	technical_description: str

	@abstractmethod
	def build(self, config: BuildConfig) -> BuildResult:
		raise NotImplementedError
