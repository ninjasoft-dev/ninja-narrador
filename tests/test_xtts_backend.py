"""Testes das adaptações leves do backend XTTS."""

import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from ninja_narrator.backends.xtts import XttsBackend


def test_transformers_compatibility_restores_removed_alias() -> None:
    """Restaura o alias esperado pelo Coqui sem substituir uma biblioteca."""
    pytorch_utils = SimpleNamespace()
    transformers = ModuleType("transformers")
    transformers.pytorch_utils = pytorch_utils  # type: ignore[attr-defined]
    torch_isin = object()
    torch = SimpleNamespace(isin=torch_isin)

    with patch.dict(sys.modules, {"transformers": transformers}):
        XttsBackend._patch_transformers_compatibility(torch)

    assert pytorch_utils.isin_mps_friendly is torch_isin
