"""Interface de linha de comando do NinjaSoft Narrator."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .config import load_config
from .domain import DevicePreference, NarrationRequest, ReferenceMode, TextEntry
from .io_utils import list_text_files, list_voice_references, read_text_file
from .service import NarrationService


def build_parser() -> argparse.ArgumentParser:
    """Constrói o parser sem executar efeitos colaterais."""
    parser = argparse.ArgumentParser(
        prog="ninja-narrator",
        description="Gere narrações locais com clonagem de voz por XTTS-v2.",
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Texto digitado para narrar.")
    source.add_argument(
        "--text-file", type=Path, action="append", help="Arquivo TXT; pode ser repetido."
    )
    parser.add_argument("--name", default="narracao", help="Nome da saída do texto digitado.")
    parser.add_argument("--reference-dir", type=Path, help="Biblioteca de amostras de voz.")
    parser.add_argument("--output-dir", type=Path, help="Diretório dos áudios gerados.")
    parser.add_argument("--reference", help="Voz usada no modo single.")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in ReferenceMode],
        help="single, combine ou per_reference.",
    )
    parser.add_argument("--speed", type=float, help="Velocidade entre 0.5 e 2.0.")
    parser.add_argument("--target-duration", type=float, help="Duração final em segundos.")
    parser.add_argument(
        "--device", choices=[device.value for device in DevicePreference], help="auto, cuda ou cpu."
    )
    parser.add_argument("--list-voices", action="store_true", help="Lista as vozes e encerra.")
    parser.add_argument(
        "--aceito-licenca-modelo",
        action="store_true",
        help="Confirma o aceite da licença CPML do XTTS-v2.",
    )
    parser.add_argument(
        "--tenho-autorizacao-da-voz",
        action="store_true",
        help="Confirma autorização para usar as amostras selecionadas.",
    )
    return parser


def _entries_from_arguments(args: argparse.Namespace, input_dir: Path) -> tuple[TextEntry, ...]:
    """Converte a origem escolhida em textos de domínio."""
    if args.text:
        return (TextEntry(name=args.name, text=args.text.strip()),)
    paths = args.text_file or list_text_files(input_dir)
    return tuple(
        TextEntry(name=path.stem, text=read_text_file(path), source_path=path) for path in paths
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Executa a CLI e retorna um código adequado ao terminal."""
    args = build_parser().parse_args(argv)
    config = load_config()
    reference_dir = (args.reference_dir or config.reference_dir).resolve()
    output_dir = (args.output_dir or config.output_dir).resolve()

    if args.list_voices:
        references = list_voice_references(reference_dir)
        if not references:
            print("Nenhuma voz encontrada.")
            return 1
        for reference in references:
            print(f"{reference.token}\t{reference.label}")
        return 0

    request = NarrationRequest(
        entries=_entries_from_arguments(args, config.input_dir),
        reference_dir=reference_dir,
        output_dir=output_dir,
        mode=ReferenceMode(args.mode or config.reference_mode.value),
        selected_reference=args.reference,
        speed=args.speed if args.speed is not None else config.speed,
        target_duration=(
            args.target_duration if args.target_duration is not None else config.target_duration
        ),
        language=config.language,
        model_name=config.model_name,
        device=DevicePreference(args.device or config.device.value),
        model_license_accepted=args.aceito_licenca_modelo,
        voice_use_authorized=args.tenho_autorizacao_da_voz,
    )

    try:
        result = NarrationService().narrate(
            request, progress_callback=lambda event: print(event.message)
        )
    except (FileNotFoundError, PermissionError, RuntimeError, ValueError) as error:
        print(f"Erro: {error}")
        return 2
    return 0 if result.failure_count == 0 else 1
