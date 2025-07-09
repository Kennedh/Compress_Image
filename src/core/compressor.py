from PIL import Image
from .models import CompressionOptions
import os

class ImageCompressor:
    def __init__(self, img: Image.Image, options: CompressionOptions) -> None:
        self._img = img
        self.options = options

    def compress(self, output_path: str):
        format_map = { 'jpeg': 'JPEG', 'png': 'PNG' }
        fmt = format_map.get(self.options.format).lower()

        q = self.options.quality or 85
        min = 5

        if self.options.max_size_kb:
            while q >= min:
                self._img.save(output_path, fmt, optimize=True, quality=q)
                size_kb = os.path.getsize(output_path) / 1024
                if size_kb <= self.options.max_size_kb:
                    return size_kb
                q -= 5
        else:
            self._img.save(output_path, fmt, optimize=True, quality=q)
            size_kb = os.path.getsize(output_path) / 1024
            return size_kb
        
        return os.path.getsize(output_path) / 1024