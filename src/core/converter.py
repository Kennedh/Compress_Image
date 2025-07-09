from PIL import Image

class ImageConverter:
    def __init__(self, img: Image.Image) -> None:
        self.formats = { 
            "jpeg": img.convert('RGB'), 
            "png": img.convert('P', palette=Image.ADAPTIVE, colors=64) 
        }

    def to(self, fmt: str, default: str = 'jpeg') -> Image.Image:
        fmt_raw = self.formats.get(fmt)

        if fmt_raw is None:
            raise ValueError(f"Formato inválido: {self.options.format}. Esperado um dos: {list(self.formats.keys())}")
        return fmt_raw