from __future__ import annotations

from abc import ABC, abstractmethod

from stockm2.models.buffett import BuffettInput


class FundamentalsProvider(ABC):
    @abstractmethod
    def get_annual_buffett_input(self, ticker: str, years: int) -> BuffettInput:
        raise NotImplementedError


class ProviderError(RuntimeError):
    """Raised when a provider cannot supply normalized Buffett inputs."""
