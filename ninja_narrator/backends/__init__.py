"""Backends de síntese disponíveis para o NinjaSoft Narrator."""

from .base import SpeechBackend
from .xtts import XttsBackend

__all__ = ["SpeechBackend", "XttsBackend"]
