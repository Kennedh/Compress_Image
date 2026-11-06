"""Entrada desktop e CLI. O motor importável fica em image_engine.py."""

import argparse
from dataclasses import replace
import sys

from compression_common import CompressionError, format_size
from image_engine import PRESETS, compress_image, settings_for_preset


def main(argv=None):
    parser = argparse.ArgumentParser(description="Comprime imagens. Sem argumentos, abre a interface.")
    parser.add_argument("input_file", nargs="?")
    parser.add_argument("output_file", nargs="?")
    parser.add_argument("-p", "--preset", choices=PRESETS, default="balanced")
    parser.add_argument("--format", choices=("JPEG", "PNG", "WEBP"))
    parser.add_argument("--quality", type=int)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--max-size-kb", type=float)
    parser.add_argument("--force", action="store_true", help="Permite substituir uma saída existente.")
    parser.add_argument("--gui", action="store_true")
    args = parser.parse_args(argv)
    if args.gui or (args.input_file is None and args.output_file is None):
        if args.input_file or args.output_file:
            parser.error("Use --gui sem caminhos de arquivos.")
        from image_gui import launch
        launch()
        return 0
    if not args.input_file or not args.output_file:
        parser.error("Informe os dois caminhos: imagem de entrada e imagem de saída.")
    options = {name: value for name, value in vars(args).items()
               if name in ("format", "quality", "width", "height", "max_size_kb") and value is not None}
    try:
        settings = replace(settings_for_preset(args.preset), **options)
        result = compress_image(args.input_file, args.output_file, settings=settings, overwrite=args.force)
    except (CompressionError, OSError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    print(f"Salvo em: {result.output_path}")
    print(f"{format_size(result.original_size)} -> {format_size(result.compressed_size)}"
          f" | redução de {result.reduction_percent:.1f}% | {result.width} x {result.height} px")
    for note in result.notes:
        print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
