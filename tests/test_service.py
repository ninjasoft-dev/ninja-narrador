"""Testes da orquestração com um backend leve em memória."""

from collections.abc import Sequence
from pathlib import Path
from threading import Event

from ninja_narrator.domain import NarrationRequest, ReferenceMode, TextEntry
from ninja_narrator.service import NarrationService


class FakeBackend:
    """Simula o backend sem carregar modelo ou produzir áudio real."""

    device = "test-device"

    def load(self) -> None:
        """Mantém o contrato do backend sem trabalho adicional."""

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
        """Registra um WAV fictício para validar o fluxo."""
        output_path.write_bytes(b"RIFF")
        return target_duration or 1.25


def request_for(tmp_path: Path, mode: ReferenceMode) -> NarrationRequest:
    """Prepara diretórios e uma solicitação de teste."""
    references = tmp_path / "voices"
    references.mkdir()
    (references / "voz-a.wav").touch()
    (references / "voz-b.wav").touch()
    return NarrationRequest(
        entries=(TextEntry(name="Boas-vindas", text="Olá."),),
        reference_dir=references,
        output_dir=tmp_path / "output",
        mode=mode,
        selected_reference="voz-a.wav",
        model_license_accepted=True,
        voice_use_authorized=True,
    )


def test_single_mode_generates_one_output(tmp_path: Path) -> None:
    """Usa somente a amostra selecionada no modo de voz única."""
    service = NarrationService(lambda _request, _status: FakeBackend())
    result = service.narrate(request_for(tmp_path, ReferenceMode.SINGLE))
    assert result.success_count == 1
    assert result.generated[0].path.name == "Boas-vindas_voz-a.wav"
    assert result.device == "test-device"


def test_per_reference_mode_generates_one_output_per_voice(tmp_path: Path) -> None:
    """Produz versões comparáveis para todas as vozes da biblioteca."""
    service = NarrationService(lambda _request, _status: FakeBackend())
    result = service.narrate(request_for(tmp_path, ReferenceMode.PER_REFERENCE))
    assert result.success_count == 2
    assert not result.failures


def test_combine_mode_passes_all_references(tmp_path: Path) -> None:
    """Agrupa a biblioteca em uma única síntese no modo combinado."""
    service = NarrationService(lambda _request, _status: FakeBackend())
    result = service.narrate(request_for(tmp_path, ReferenceMode.COMBINE))
    assert result.success_count == 1
    assert len(result.generated[0].references) == 2
    assert result.generated[0].path.name.endswith("_combinada.wav")


def test_pre_cancelled_request_does_not_synthesize(tmp_path: Path) -> None:
    """Respeita um cancelamento recebido antes do primeiro trabalho."""
    cancellation = Event()
    cancellation.set()
    service = NarrationService(lambda _request, _status: FakeBackend())
    result = service.narrate(
        request_for(tmp_path, ReferenceMode.COMBINE), cancellation=cancellation
    )
    assert result.cancelled
    assert result.success_count == 0


def test_missing_voice_library_fails_before_backend_load(tmp_path: Path) -> None:
    """Explica a ausência de amostras sem reservar recursos do modelo."""
    request = NarrationRequest(
        entries=(TextEntry(name="texto", text="Olá."),),
        reference_dir=tmp_path / "vazia",
        output_dir=tmp_path / "out",
        mode=ReferenceMode.COMBINE,
        model_license_accepted=True,
        voice_use_authorized=True,
    )
    service = NarrationService(lambda _request, _status: FakeBackend())
    try:
        service.narrate(request)
    except FileNotFoundError as error:
        assert "Nenhuma amostra" in str(error)
    else:
        raise AssertionError("Era esperada uma falha por biblioteca vazia.")
