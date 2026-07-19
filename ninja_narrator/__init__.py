"""Núcleo do NinjaSoft Narrator, narrador local e open source da NinjaSoft."""

from .config import NarratorConfig, load_config
from .domain import NarrationRequest, NarrationResult, ReferenceMode, TextEntry
from .service import NarrationService

__all__ = [
    "NarrationRequest",
    "NarrationResult",
    "NarrationService",
    "NarratorConfig",
    "ReferenceMode",
    "TextEntry",
    "load_config",
]

__version__ = "1.0.1"
