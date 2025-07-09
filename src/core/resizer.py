from PIL import Image
from .models import ResizeOptions

class ImageResizer:
    def resize(self, img: Image.Image, options: ResizeOptions) -> Image.Image:
        if options.keep_aspect_ratio:
            img.thumbnail(
                (
                    options.max_width or img.width,
                    options.max_height or img.height
                ),
                Image.LANCZOS
            )
        else:
            img = img.resize(
                (
                    options.max_width or img.width,
                    options.max_height or img.height
                ),
                Image.LANCZOS
            )
        return img
