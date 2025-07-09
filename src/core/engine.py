from PIL import Image
from .compressor import ImageCompressor
from .converter import ImageConverter
from .resizer import ImageResizer
from .models import CompressionOptions, ResizeOptions

class CompressionEngine: 
    def __init__(self, 
        input_path: str,
        output_path: str,
        resize_opts: ResizeOptions,
        comp_opts: CompressionOptions
    ):
        self.output_path = output_path
        self.resize_opts = resize_opts
        self.comp_opts = comp_opts
        self.img = Image.open(input_path)
        self.compressor = ImageCompressor(self.img, comp_opts)
        self.converter = ImageConverter(self.img)
        self.resizer = ImageResizer()

    def run(self) -> None:

        self.img = self.resizer.resize(self.img, self.resize_opts)

        self.img = self.converter.to(self.comp_opts.format)

        final_size_kb = self.compressor.compress(self.output_path)
        print(f"Imagem salva com sucesso em {self.output_path}. Tamanho final: {final_size_kb:.2f} KB")
    