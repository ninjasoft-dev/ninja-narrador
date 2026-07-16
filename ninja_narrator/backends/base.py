"""Contrato comum para mecanismos de síntese de voz."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol


class SpeechBackend(Protocol):
    """Interface mínima implementada por um backend de narração."""

    @property
    def device(self) -> str:
        """Informa o dispositivo realmente usado pelo modelo."""

    def load(self) -> None:
        """Carrega o modelo sob demanda."""

    def synthesize(
        self,
        text: str,
        references: Sequence[Path],
        output_path: Path,
        *,
        language: str,
        speed: float,
        target_duration: float | None,
    ) -> float:
        """Gera áudio e retorna sua duração final em segundos."""
