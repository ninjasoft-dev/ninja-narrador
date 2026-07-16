"""Testes do carregamento de configuração local."""

from pathlib import Path

from ninja_narrator.config import load_config
from ninja_narrator.domain import DevicePreference, ReferenceMode


def test_load_config_reads_toml_and_environment(tmp_path: Path, monkeypatch) -> None:
    """Variáveis de ambiente sobrescrevem somente os valores desejados."""
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[narrator]
reference_mode = "combine"
speed = 1.25
device = "cpu"
output_dir = "entregas"
""".strip(),
        encoding="utf-8",
    )
    custom_output = tmp_path / "saidas"
    monkeypatch.setenv("NINJA_NARRATOR_OUTPUT_DIR", str(custom_output))

    config = load_config(config_path)

    assert config.reference_mode is ReferenceMode.COMBINE
    assert config.device is DevicePreference.CPU
    assert config.speed == 1.25
    assert config.output_dir == custom_output
    assert custom_output.is_dir()


def test_missing_config_uses_safe_defaults(tmp_path: Path, monkeypatch) -> None:
    """A ausência do TOML não impede a inicialização."""
    reference_dir = tmp_path / "vozes"
    monkeypatch.setenv("NINJA_NARRATOR_REFERENCE_DIR", str(reference_dir))
    config = load_config(tmp_path / "ausente.toml")
    assert config.reference_mode is ReferenceMode.SINGLE
    assert reference_dir.is_dir()
