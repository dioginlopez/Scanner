from __future__ import annotations

import argparse

from .analyzer import run_live_capture


def _non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("deve ser maior ou igual a zero")
    return parsed


def _sample_count(value: str) -> int:
    parsed = int(value)
    if parsed < 10:
        raise argparse.ArgumentTypeError("deve ser de pelo menos 10")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fc26-face-scanner",
        description="Escaneia o rosto pela webcam e gera sugestões para sliders do FC26.",
    )
    parser.add_argument(
        "--camera-index",
        type=_non_negative_int,
        default=0,
        help="Índice da webcam (padrão: 0)",
    )
    parser.add_argument(
        "--samples",
        type=_sample_count,
        default=45,
        help="Número de amostras válidas (mínimo: 10)",
    )
    parser.add_argument("--output-dir", type=str, default="output", help="Pasta de saída")
    parser.add_argument(
        "--no-preview",
        action="store_true",
        help="Desativa janela de preview da câmera",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = run_live_capture(
        camera_index=args.camera_index,
        sample_count=args.samples,
        output_dir=args.output_dir,
        show_preview=not args.no_preview,
    )
    print("\nAnálise concluída com sucesso.")
    print(f"Relatório JSON: {result.report_json_path}")
    print(f"Relatório Markdown: {result.report_markdown_path}")


if __name__ == "__main__":
    main()
