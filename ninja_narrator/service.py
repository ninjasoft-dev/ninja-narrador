"""Orquestração da narração sem dependência da interface gráfica."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from threading import Event

from .backends.base import SpeechBackend
from .backends.xtts import XttsBackend
from .domain import (
    GeneratedAudio,
    NarrationFailure,
    NarrationRequest,
    NarrationResult,
    ProgressCallback,
    ProgressEvent,
    ReferenceMode,
    TextEntry,
    VoiceReference,
)
from .io_utils import list_voice_references, safe_filename, select_reference

BackendFactory = Callable[[NarrationRequest, Callable[[str], None]], SpeechBackend]


def _default_backend_factory(
    request: NarrationRequest, status_callback: Callable[[str], None]
) -> SpeechBackend:
    """Cria o backend padrão com os parâmetros validados da execução."""
    return XttsBackend(
        request.model_name,
        request.device,
        license_accepted=request.model_license_accepted,
        status_callback=status_callback,
    )


class NarrationService:
    """Transforma uma solicitação validada em um ou mais arquivos de áudio."""

    def __init__(self, backend_factory: BackendFactory | None = None) -> None:
        """Permite trocar o backend em testes ou integrações futuras."""
        self._backend_factory = backend_factory or _default_backend_factory

    @staticmethod
    def _notify(callback: ProgressCallback | None, stage: str, message: str) -> None:
        """Publica progresso estruturado apenas quando houver observador."""
        if callback:
            callback(ProgressEvent(stage=stage, message=message))

    @staticmethod
    def _reference_groups(
        request: NarrationRequest, references: list[VoiceReference]
    ) -> list[tuple[str, tuple[Path, ...]]]:
        """Monta os grupos de amostras conforme o modo escolhido."""
        if not references:
            raise FileNotFoundError(
                "Nenhuma amostra de voz foi encontrada na biblioteca selecionada."
            )
        if request.mode is ReferenceMode.COMBINE:
            return [("combinada", tuple(item.path for item in references))]
        if request.mode is ReferenceMode.SINGLE:
            chosen = select_reference(request.selected_reference or "", references)
            return [(safe_filename(chosen.path.stem, "voz"), (chosen.path,))]
        return [
            (safe_filename(reference.path.stem, "voz"), (reference.path,))
            for reference in references
        ]

    @staticmethod
    def _output_path(entry: TextEntry, voice_label: str, output_dir: Path) -> Path:
        """Cria um nome de saída previsível para texto e voz."""
        text_name = safe_filename(entry.name)
        return output_dir / f"{text_name}_{voice_label}.wav"

    def narrate(
        self,
        request: NarrationRequest,
        *,
        progress_callback: ProgressCallback | None = None,
        cancellation: Event | None = None,
    ) -> NarrationResult:
        """Executa os trabalhos de síntese e preserva falhas isoladas."""
        request.validate()
        request.output_dir.mkdir(parents=True, exist_ok=True)
        references = list_voice_references(request.reference_dir)
        groups = self._reference_groups(request, references)
        cancellation = cancellation or Event()

        def backend_status(message: str) -> None:
            """Adapta mensagens simples do backend para eventos de progresso."""
            self._notify(progress_callback, "modelo", message)

        backend = self._backend_factory(request, backend_status)
        result = NarrationResult(device="não carregado")
        total_jobs = len(request.entries) * len(groups)
        completed_jobs = 0

        if cancellation.is_set():
            result.cancelled = True
            self._notify(progress_callback, "cancelado", "Narração cancelada.")
            return result
        try:
            backend.load()
        except Exception as error:
            raise RuntimeError(f"Não foi possível carregar o modelo: {error}") from error
        result.device = backend.device

        for entry in request.entries:
            for voice_label, reference_paths in groups:
                if cancellation.is_set():
                    result.cancelled = True
                    self._notify(progress_callback, "cancelado", "Narração cancelada.")
                    return result

                output_path = self._output_path(entry, voice_label, request.output_dir)
                self._notify(
                    progress_callback,
                    "sintese",
                    f"Narrando '{entry.name}' com {voice_label}…",
                )
                try:
                    duration = backend.synthesize(
                        entry.text,
                        reference_paths,
                        output_path,
                        language=request.language,
                        speed=request.speed,
                        target_duration=request.target_duration,
                    )
                except Exception as error:
                    result.failures.append(
                        NarrationFailure(entry_name=entry.name, reason=str(error))
                    )
                    self._notify(
                        progress_callback,
                        "erro",
                        f"Falha ao narrar '{entry.name}': {error}",
                    )
                else:
                    result.generated.append(
                        GeneratedAudio(
                            path=output_path,
                            references=reference_paths,
                            duration_seconds=duration,
                        )
                    )
                completed_jobs += 1
                self._notify(
                    progress_callback,
                    "progresso",
                    f"{completed_jobs} de {total_jobs} etapas concluídas.",
                )

        result.device = backend.device
        self._notify(
            progress_callback,
            "concluido",
            f"{result.success_count} áudio(s) gerado(s).",
        )
        return result
