"""Pós-processamento de áudio gerado pelos backends."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def fit_audio_to_duration(
    waveform: Any,
    sample_rate: int,
    target_duration: float | None,
    warning_callback: Callable[[str], None] | None = None,
) -> tuple[Any, float]:
    """Ajusta a duração do áudio preservando o tom da voz."""
    import librosa
    import numpy as np

    audio = np.asarray(waveform, dtype=np.float32).squeeze()
    current_duration = float(audio.shape[-1] / sample_rate) if audio.size else 0.0
    if target_duration is None or current_duration <= 0:
        return audio, current_duration
    if target_duration <= 0:
        raise ValueError("A duração alvo deve ser maior que zero.")

    stretch_rate = current_duration / target_duration
    if not 0.5 <= stretch_rate <= 2.0 and warning_callback:
        warning_callback("O ajuste de duração é agressivo e pode reduzir a naturalidade da voz.")

    adjusted = librosa.effects.time_stretch(audio, rate=stretch_rate)
    target_samples = max(1, round(target_duration * sample_rate))
    if adjusted.shape[-1] > target_samples:
        adjusted = adjusted[:target_samples]
    elif adjusted.shape[-1] < target_samples:
        adjusted = np.pad(adjusted, (0, target_samples - adjusted.shape[-1]))
    return adjusted.astype(np.float32), current_duration
