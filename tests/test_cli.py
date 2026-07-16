"""Testes dos fluxos leves da interface de terminal."""

from pathlib import Path

from ninja_narrator import cli
from ninja_narrator.config import NarratorConfig


def test_list_voices_prints_token(tmp_path: Path, monkeypatch, capsys) -> None:
    """A listagem informa o token aceito por --reference."""
    reference_dir = tmp_path / "voices"
    reference_dir.mkdir()
    (reference_dir / "narrador.wav").touch()
    config = NarratorConfig(tmp_path, tmp_path / "out", reference_dir)
    monkeypatch.setattr(cli, "load_config", lambda: config)

    exit_code = cli.main(["--list-voices"])

    assert exit_code == 0
    assert "narrador.wav" in capsys.readouterr().out


def test_cli_rejects_synthesis_without_consents(tmp_path: Path, monkeypatch, capsys) -> None:
    """A CLI não inicia o modelo sem as duas confirmações."""
    reference_dir = tmp_path / "voices"
    reference_dir.mkdir()
    (reference_dir / "voz.wav").touch()
    config = NarratorConfig(tmp_path, tmp_path / "out", reference_dir)
    monkeypatch.setattr(cli, "load_config", lambda: config)

    exit_code = cli.main(["--text", "Teste.", "--mode", "single", "--reference", "voz.wav"])

    assert exit_code == 2
    assert "autorização" in capsys.readouterr().out
