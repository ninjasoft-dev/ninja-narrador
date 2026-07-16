"""Objetos de domínio compartilhados pela CLI, interface e serviço de narração."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from threading import Event


class ReferenceMode(str, Enum):
    """Define como as amostras de voz participam de cada síntese."""

    SINGLE = "single"
    COMBINE = "combine"
    PER_REFERENCE = "per_reference"


class DevicePreference(str, Enum):
    """Dispositivos que podem ser solicitados ao backend local."""

    AUTO = "auto"
    CUDA = "cuda"
    CPU = "cpu"


@dataclass(frozen=True, slots=True)
class TextEntry:
    """Texto pronto para síntese e nome usado no arquivo de saída."""

    name: str
    text: str
    source_path: Path | None = None


@dataclass(frozen=True, slots=True)
class VoiceReference:
    """Amostra de voz descoberta na biblioteca configurada."""

    path: Path
    relative_path: Path
    label: str
    token: str


@dataclass(frozen=True, slots=True)
class NarrationRequest:
    """Parâmetros validados de uma execução de narração."""

    entries: tuple[TextEntry, ...]
    reference_dir: Path
    output_dir: Path
    mode: ReferenceMode = ReferenceMode.SINGLE
    selected_reference: str | None = None
    speed: float = 1.0
    target_duration: float | None = None
    language: str = "pt"
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    device: DevicePreference = DevicePreference.AUTO
    model_license_accepted: bool = False
    voice_use_authorized: bool = False

    def validate(self) -> None:
        """Rejeita combinações inválidas antes de carregar o modelo pesado."""
        if not self.entries:
            raise ValueError("Informe ao menos um texto para narrar.")
        if any(not entry.text.strip() for entry in self.entries):
            raise ValueError("O texto da narração não pode estar vazio.")
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError("A velocidade deve estar entre 0,5 e 2,0.")
        if self.target_duration is not None and self.target_duration <= 0:
            raise ValueError("A duração alvo deve ser maior que zero.")
        if self.mode is ReferenceMode.SINGLE and not self.selected_reference:
            raise ValueError("Escolha uma voz para o modo de referência única.")
        if not self.voice_use_authorized:
            raise ValueError("Confirme que você tem autorização para usar a voz selecionada.")
        if not self.model_license_accepted:
            raise ValueError("Leia e aceite a licença do modelo XTTS-v2 antes de continuar.")


@dataclass(frozen=True, slots=True)
class GeneratedAudio:
    """Arquivo de áudio produzido com as referências que o originaram."""

    path: Path
    references: tuple[Path, ...]
    duration_seconds: float


@dataclass(frozen=True, slots=True)
class NarrationFailure:
    """Falha isolada que não impediu o processamento dos demais textos."""

    entry_name: str
    reason: str


@dataclass(slots=True)
class NarrationResult:
    """Resumo completo de uma execução de narração."""

    device: str
    generated: list[GeneratedAudio] = field(default_factory=list)
    failures: list[NarrationFailure] = field(default_factory=list)
    cancelled: bool = False

    @property
    def success_count(self) -> int:
        """Retorna quantos arquivos de áudio foram gerados."""
        return len(self.generated)

    @property
    def failure_count(self) -> int:
        """Retorna quantos textos ou jobs falharam."""
        return len(self.failures)


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """Mensagem estruturada enviada à interface durante a execução."""

    stage: str
    message: str


ProgressCallback = Callable[[ProgressEvent], None]
CancellationToken = Event
