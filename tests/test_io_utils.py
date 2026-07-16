"""Testes de nomes, textos e biblioteca de vozes."""

from pathlib import Path

import pytest

from ninja_narrator.io_utils import (
    list_voice_references,
    read_text_file,
    safe_filename,
    select_reference,
)


def test_safe_filename_removes_accents_and_reserved_characters() -> None:
    """Gera um nome portátil sem perder a intenção do título."""
    assert safe_filename('Capítulo 01: "Introdução"') == "Capitulo_01_Introducao"


def test_read_text_file_accepts_windows_encoding(tmp_path: Path) -> None:
    """Lê corretamente um TXT legado em CP-1252."""
    text_path = tmp_path / "legado.txt"
    text_path.write_bytes("Narração em português".encode("cp1252"))
    assert read_text_file(text_path) == "Narração em português"


def test_voice_library_is_recursive_and_neutral(tmp_path: Path) -> None:
    """Descobre subpastas sem atribuir características à voz."""
    voice_path = tmp_path / "projeto" / "voz-principal.wav"
    voice_path.parent.mkdir()
    voice_path.touch()
    references = list_voice_references(tmp_path)
    assert references[0].label == "voz principal"
    assert references[0].token == "projeto/voz-principal.wav"


def test_select_reference_rejects_ambiguous_names(tmp_path: Path) -> None:
    """Evita escolher silenciosamente uma voz quando nomes se repetem."""
    for directory in (tmp_path / "a", tmp_path / "b"):
        directory.mkdir()
        (directory / "voz.wav").touch()
    references = list_voice_references(tmp_path)
    with pytest.raises(ValueError, match="ambígua"):
        select_reference("voz.wav", references)
