"""Integração local com o modelo XTTS-v2 do Coqui TTS."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from ..audio import fit_audio_to_duration
from ..domain import DevicePreference

DEFAULT_SYNTHESIS_OPTIONS = {
    "sound_norm_refs": True,
    "temperature": 0.65,
    "top_p": 0.8,
    "top_k": 50,
    "repetition_penalty": 10.0,
    "length_penalty": 1.0,
    "gpt_cond_len": 15,
    "gpt_cond_chunk_len": 5,
    "max_ref_len": 15,
}


class XttsBackend:
    """Carrega o XTTS-v2 sob demanda e gera arquivos WAV localmente."""

    def __init__(
        self,
        model_name: str,
        device_preference: DevicePreference = DevicePreference.AUTO,
        *,
        license_accepted: bool,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Configura o backend sem carregar pesos pesados na memória."""
        self.model_name = model_name
        self.device_preference = device_preference
        self.license_accepted = license_accepted
        self.status_callback = status_callback
        self._model: Any | None = None
        self._device = "não carregado"

    @property
    def device(self) -> str:
        """Retorna o dispositivo escolhido após carregar o modelo."""
        return self._device

    def _notify(self, message: str) -> None:
        """Encaminha uma mensagem quando houver observador registrado."""
        if self.status_callback:
            self.status_callback(message)

    def _resolve_device(self, torch: Any) -> str:
        """Valida a preferência e seleciona CUDA ou CPU."""
        if self.device_preference is DevicePreference.CPU:
            return "cpu"
        if torch.cuda.is_available():
            try:
                torch.zeros(1, device="cuda")
                torch.cuda.synchronize()
                return "cuda"
            except Exception as error:
                if self.device_preference is DevicePreference.CUDA:
                    raise RuntimeError("A GPU CUDA selecionada não está disponível.") from error
                self._notify("CUDA indisponível; a execução continuará na CPU.")
        if self.device_preference is DevicePreference.CUDA:
            raise RuntimeError("CUDA não está disponível neste computador.")
        return "cpu"

    @staticmethod
    def _patch_torch_checkpoint_loading(torch: Any) -> None:
        """Mantém compatibilidade do Coqui com o padrão do PyTorch 2.6+."""
        if getattr(torch.load, "_ninja_narrator_compat", False):
            return
        original_load = torch.load

        def compatible_load(*args: Any, **kwargs: Any) -> Any:
            """Restaura a leitura completa esperada pelos checkpoints legados."""
            kwargs.setdefault("weights_only", False)
            return original_load(*args, **kwargs)

        compatible_load._ninja_narrator_compat = True  # type: ignore[attr-defined]
        torch.load = compatible_load

    @staticmethod
    def _patch_transformers_compatibility(torch: Any) -> None:
        """Restaura o alias de conjunto removido no Transformers 5."""
        try:
            from transformers import pytorch_utils
        except ImportError:
            return
        if not hasattr(pytorch_utils, "isin_mps_friendly"):
            pytorch_utils.isin_mps_friendly = torch.isin

    @staticmethod
    def _patch_typeguard_for_bundle() -> None:
        """Evita inspeção incompatível do typeguard em executáveis congelados."""
        if not getattr(sys, "frozen", False):
            return
        try:
            import typeguard
            from typeguard import _decorators
        except ImportError:
            return

        def passthrough(target: Any = None, **_kwargs: Any) -> Any:
            """Mantém o objeto original quando a inspeção não funciona no bundle."""
            if target is None:
                return lambda decorated: decorated
            return target

        typeguard.typechecked = passthrough
        _decorators.typechecked = passthrough

    def load(self) -> None:
        """Carrega o modelo uma única vez depois do aceite explícito da licença."""
        if self._model is not None:
            return
        if not self.license_accepted:
            raise PermissionError("A licença do modelo XTTS-v2 não foi aceita.")

        # A variável só é definida depois da confirmação explícita na GUI ou CLI.
        os.environ["COQUI_TOS_AGREED"] = "1"
        import torch

        self._patch_transformers_compatibility(torch)
        from TTS.api import TTS

        self._patch_torch_checkpoint_loading(torch)
        self._patch_typeguard_for_bundle()
        self._device = self._resolve_device(torch)
        self._notify(f"Carregando XTTS-v2 em {self._device.upper()}…")
        self._model = TTS(self.model_name).to(self._device)
        self._notify("Modelo pronto para narrar.")

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
        """Sintetiza um texto, ajusta duração opcional e salva o WAV."""
        self.load()
        if self._model is None:  # proteção para analisadores estáticos
            raise RuntimeError("O modelo XTTS-v2 não foi carregado.")
        if not references:
            raise ValueError("Nenhuma amostra de voz foi informada.")

        speaker_wav: str | list[str]
        if len(references) == 1:
            speaker_wav = str(references[0])
        else:
            speaker_wav = [str(path) for path in references]

        waveform = self._model.synthesizer.tts(
            text=text,
            speaker_name=None,
            language_name=language,
            speaker_wav=speaker_wav,
            split_sentences=True,
            speed=speed,
            **DEFAULT_SYNTHESIS_OPTIONS,
        )
        sample_rate = self._model.synthesizer.output_sample_rate
        adjusted, _original_duration = fit_audio_to_duration(
            waveform, sample_rate, target_duration, self._notify
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._model.synthesizer.save_wav(wav=adjusted, path=str(output_path))
        return float(adjusted.shape[-1] / sample_rate)
