from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.models import ModelCapability, ModelConfig


@runtime_checkable
class ModelRegistry(Protocol):
    """Protocol for LLM model configuration registry."""

    async def get_model(self, model_identifier: str) -> ModelConfig | None:
        """Resolve model alias or name to an active ModelConfig.
        
        Args:
            model_identifier: The logical name (e.g., 'gpt-4') or alias.
        """

    async def list_models(
        self,
        *,
        provider: str | None = None,
        capability: ModelCapability | None = None,
        active_only: bool = True,
    ) -> list[ModelConfig]:
        """List all available models with optional filtering."""

    async def get_fallback_chain(self, failed_model: str) -> list[ModelConfig]:
        """Get an ordered list of fallback models based on priority and similarities."""

    async def refresh(self) -> None:
        """Manually trigger a refresh of the registry data from the source."""
