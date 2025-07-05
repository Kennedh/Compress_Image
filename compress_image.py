import os
import argparse
from PIL import Image

def compress_image(input_path, output_path, max_width=None, max_height=None, max_size_kb=None, quality=None, to_jpeg=False, redim=False):
    img = Image.open(input_path)
    original_size = os.path.getsize(input_path) / 1024

    if redim:
        # Redimensiona mantendo proporção
        if max_width or max_height:
            img.thumbnail((max_width if max_width else img.width, max_height if max_height else img.height), Image.LANCZOS)
    else:
        # Força os pixels colocados no parametro
        if max_width and max_height:
            img = img.resize((max_width, max_height), Image.LANCZOS)
        elif max_width:
            img = img.resize((max_width, img.height), Image.LANCZOS)
        elif max_height:
            img = img.resize((img.width, max_height), Image.LANCZOS)

    if to_jpeg:
        img = img.convert('RGB')
        ext = 'JPEG'

        if max_size_kb:
            # Loop para reduzir qualidade até atingir o tamanho máximo desejado
            q = quality if quality else 85
            while q >= 5:
                img.save(output_path, ext, optimize=True, quality=q)
                final_size = os.path.getsize(output_path) / 1024
                if final_size <= max_size_kb:
                    break
                q -= 5
        else:
            img.save(output_path, ext, optimize=True, quality=quality)
            final_size = os.path.getsize(output_path) / 1024
    else:
        # Quantiza para cores indexadas (ex: 64 cores)
        img = img.convert('P', palette=Image.ADAPTIVE, colors=64)
        ext = 'PNG'
        img.save(output_path, ext, optimize=True)
        final_size = os.path.getsize(output_path) / 1024

        if max_size_kb:
            # Loop para reduzir qualidade até atingir o tamanho máximo desejado
            q = quality if quality else 85
            while q >= 5:
                img.save(output_path, ext, optimize=True, quality=q)
                final_size = os.path.getsize(output_path) / 1024
                if final_size <= max_size_kb:
                    break
                q -= 5
        else:
            img.save(output_path, ext, optimize=True, quality=quality)
            final_size = os.path.getsize(output_path) / 1024

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compress and resize images efficiently.")
    parser.add_argument("input", help="Caminho da imagem de entrada")
    parser.add_argument("output", help="Caminho da imagem de saída")
    parser.add_argument("--max-width", type=int, help="Largura máxima")
    parser.add_argument("--max-height", type=int, help="Altura máxima")
    parser.add_argument("--max-size-kb", type=float, help="Tamanho máximo em KB (somente JPEG)")
    parser.add_argument("--quality", type=int, default=70, help="Qualidade JPEG (padrão 70)")
    parser.add_argument("--jpeg", action="store_true", help="Salvar como JPEG")
    parser.add_argument("--redim", action="store_true", help="Redimencionar a imagem respeitando a proporção")
    args = parser.parse_args()

    compress_image(
        input_path=args.input,
        output_path=args.output,
        max_width=args.max_width,
        max_height=args.max_height,
        max_size_kb=args.max_size_kb,
        quality=args.quality,
        to_jpeg=args.jpeg,
        redim=args.redim
    )
