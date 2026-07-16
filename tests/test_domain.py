"""Testes das regras de entrada da narração."""

from pathlib import Path

import pytest

from ninja_narrator.domain import NarrationRequest, ReferenceMode, TextEntry


def valid_request(tmp_path: Path) -> NarrationRequest:
    """Cria uma solicitação mínima aceita pelo domínio."""
    return NarrationRequest(
        entries=(TextEntry(name="exemplo", text="Olá, mundo."),),
        reference_dir=tmp_path,
        output_dir=tmp_path,
        mode=ReferenceMode.SINGLE,
        selected_reference="voz.wav",
        model_license_accepted=True,
        voice_use_authorized=True,
    )


def test_valid_request_is_accepted(tmp_path: Path) -> None:
    """Aceita parâmetros completos dentro dos limites."""
    valid_request(tmp_path).validate()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("speed", 2.1, "velocidade"),
        ("target_duration", 0, "duração alvo"),
        ("voice_use_authorized", False, "autorização"),
        ("model_license_accepted", False, "licença"),
    ],
)
def test_invalid_request_explains_problem(
    tmp_path: Path, field: str, value: object, message: str
) -> None:
    """Apresenta mensagens úteis para opções inseguras ou inválidas."""
    request = valid_request(tmp_path)
    object.__setattr__(request, field, value)
    with pytest.raises(ValueError, match=message):
        request.validate()
