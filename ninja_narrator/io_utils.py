"""Leitura de textos, descoberta de vozes e nomes seguros de arquivos."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .domain import VoiceReference

AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".flac", ".m4a", ".ogg"})
TEXT_EXTENSIONS = frozenset({".txt"})


def safe_filename(value: str, fallback: str = "narracao") -> str:
    """Converte um título livre em um nome portátil de arquivo."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    sanitized = re.sub(r"[^a-zA-Z0-9._-]+", "_", ascii_value).strip("._-")
    return sanitized or fallback


def read_text_file(path: Path) -> str:
    """Lê texto aceitando codificações comuns em arquivos do Windows."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            content = path.read_text(encoding=encoding).strip()
        except UnicodeDecodeError:
            continue
        if not content:
            raise ValueError(f"O arquivo '{path.name}' está vazio.")
        return content
    raise ValueError(f"Não foi possível identificar a codificação de '{path.name}'.")


def list_text_files(directory: Path) -> list[Path]:
    """Lista arquivos de texto diretamente no diretório informado."""
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS
    )


def list_audio_files(directory: Path) -> list[Path]:
    """Descobre recursivamente amostras de áudio compatíveis."""
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS
    )


def reference_label(path: Path) -> str:
    """Cria um rótulo legível sem presumir gênero ou identidade da voz."""
    label = re.sub(r"[_-]+", " ", path.stem).strip()
    return label or "Voz sem nome"


def list_voice_references(reference_dir: Path) -> list[VoiceReference]:
    """Converte a biblioteca de áudio em referências tipadas."""
    references = []
    for path in list_audio_files(reference_dir):
        relative_path = path.relative_to(reference_dir)
        references.append(
            VoiceReference(
                path=path,
                relative_path=relative_path,
                label=reference_label(path),
                token=relative_path.as_posix(),
            )
        )
    return sorted(references, key=lambda item: (item.label.casefold(), item.token))


def select_reference(token: str, references: list[VoiceReference]) -> VoiceReference:
    """Localiza uma voz por token, nome ou caminho relativo sem ambiguidades."""
    query = token.strip().replace("\\", "/").casefold()
    matches = [
        reference
        for reference in references
        if query
        in {
            reference.token.casefold(),
            reference.path.name.casefold(),
            reference.path.stem.casefold(),
            reference.label.casefold(),
        }
    ]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(reference.token for reference in matches)
        raise ValueError(f"A voz '{token}' é ambígua: {names}.")
    raise ValueError(f"A voz '{token}' não foi encontrada.")
