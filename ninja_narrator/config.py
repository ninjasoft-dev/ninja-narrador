"""Carregamento das configurações locais do Ninja Narrator."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

from .domain import DevicePreference, ReferenceMode


def application_root() -> Path:
    """Retorna o diretório usado como raiz pela aplicação."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


@dataclass(slots=True)
class NarratorConfig:
    """Reúne caminhos e preferências persistentes do narrador."""

    input_dir: Path
    output_dir: Path
    reference_dir: Path
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"
    language: str = "pt"
    device: DevicePreference = DevicePreference.AUTO
    reference_mode: ReferenceMode = ReferenceMode.SINGLE
    speed: float = 1.0
    target_duration: float | None = None

    def ensure_workspace(self) -> None:
        """Cria os diretórios operacionais que ainda não existirem."""
        for directory in (self.input_dir, self.output_dir, self.reference_dir):
            directory.mkdir(parents=True, exist_ok=True)


def _resolve_path(value: str | Path, root: Path) -> Path:
    """Resolve caminhos relativos em relação à raiz da aplicação."""
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def _read_toml(config_path: Path) -> dict[str, Any]:
    """Lê um arquivo TOML ausente sem transformar isso em erro."""
    if not config_path.exists():
        return {}
    with config_path.open("rb") as config_file:
        return tomllib.load(config_file)


def load_config(config_path: Path | None = None) -> NarratorConfig:
    """Carrega configuração de TOML e permite sobrescrita por ambiente."""
    root = application_root()
    selected_path = config_path or Path(os.getenv("NINJA_NARRATOR_CONFIG", root / "config.toml"))
    values = _read_toml(selected_path).get("narrator", {})

    def setting(environment: str, key: str, default: Any) -> Any:
        """Prioriza ambiente, depois TOML e finalmente o valor padrão."""
        return os.getenv(environment, values.get(key, default))

    target_value = setting("NINJA_NARRATOR_TARGET_DURATION", "target_duration", None)
    config = NarratorConfig(
        input_dir=_resolve_path(
            setting("NINJA_NARRATOR_INPUT_DIR", "input_dir", "input_texts"), root
        ),
        output_dir=_resolve_path(
            setting("NINJA_NARRATOR_OUTPUT_DIR", "output_dir", "output_audio"), root
        ),
        reference_dir=_resolve_path(
            setting("NINJA_NARRATOR_REFERENCE_DIR", "reference_dir", "reference_audio"),
            root,
        ),
        model_name=str(
            setting(
                "NINJA_NARRATOR_MODEL",
                "model_name",
                "tts_models/multilingual/multi-dataset/xtts_v2",
            )
        ),
        language=str(setting("NINJA_NARRATOR_LANGUAGE", "language", "pt")),
        device=DevicePreference(
            setting("NINJA_NARRATOR_DEVICE", "device", DevicePreference.AUTO.value)
        ),
        reference_mode=ReferenceMode(
            setting(
                "NINJA_NARRATOR_REFERENCE_MODE",
                "reference_mode",
                ReferenceMode.SINGLE.value,
            )
        ),
        speed=float(setting("NINJA_NARRATOR_SPEED", "speed", 1.0)),
        target_duration=float(target_value) if target_value not in (None, "") else None,
    )
    config.ensure_workspace()
    return config
