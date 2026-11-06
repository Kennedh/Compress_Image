"""Compressão de imagens com Pillow, sem dependência de Tkinter."""

from dataclasses import dataclass
from io import BytesIO
import math
import os
from pathlib import Path
import tempfile
import time

from PIL import Image, ImageCms, ImageOps, UnidentifiedImageError

from compression_common import CompressionCancelled, CompressionError, CompressionResult


PRESETS = {
    "balanced": ("Equilibrado", "Boa qualidade, mantendo as dimensões originais."),
    "web": ("Web e compartilhamento", "WebP, qualidade 78 e até 1920 × 1920 px."),
    "quality": ("Alta qualidade", "Qualidade 95, mantendo as dimensões originais."),
    "lossless": ("Sem perdas", "PNG sem reduzir cores; WebP sem perdas se escolhido."),
}
EXTENSIONS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
INPUT_EXTENSIONS = "*.jpg *.jpeg *.png *.webp *.bmp *.gif *.tif *.tiff *.ico *.ppm *.pgm *.pcx *.tga"


@dataclass(frozen=True)
class ImageSettings:
    format: str = "JPEG"
    quality: int = 85
    width: int | None = None
    height: int | None = None
    keep_ratio: bool = True
    max_size_kb: float | None = None
    lossless: bool = False

    def validate(self):
        if self.format not in EXTENSIONS:
            raise CompressionError("Escolha JPEG, PNG ou WEBP.")
        if not isinstance(self.quality, int) or not 5 <= self.quality <= 100:
            raise CompressionError("A qualidade deve estar entre 5 e 100.")
        for dimension in (self.width, self.height):
            if dimension is not None and (not isinstance(dimension, int) or dimension <= 0):
                raise CompressionError("As dimensões devem ser números inteiros positivos.")
        if self.lossless and self.format == "JPEG":
            raise CompressionError("JPEG não suporta o modo sem perdas. Escolha PNG ou WEBP.")
        if self.max_size_kb is not None:
            if not math.isfinite(self.max_size_kb) or self.max_size_kb <= 0:
                raise CompressionError("O limite em KB deve ser positivo e finito.")
            if self.format == "PNG" or self.lossless:
                raise CompressionError("O limite em KB está disponível para JPEG e WebP com perdas.")


def settings_for_preset(preset):
    if preset == "balanced":
        return ImageSettings()
    if preset == "web":
        return ImageSettings(format="WEBP", quality=78, width=1920, height=1920)
    if preset == "quality":
        return ImageSettings(quality=95)
    if preset == "lossless":
        return ImageSettings(format="PNG", lossless=True)
    raise CompressionError(f"Perfil inválido: {preset}")


@dataclass(frozen=True)
class ImageCompressionResult(CompressionResult):
    width: int
    height: int
    format: str
    quality: int | None
    kept_original: bool = False
    notes: tuple[str, ...] = ()


def _check_cancel(cancel_event):
    if cancel_event is not None and cancel_event.is_set():
        raise CompressionCancelled("Compressão cancelada.")


def load_image(path):
    """Lê os pixels, fecha o arquivo e aplica a orientação EXIF."""
    try:
        with Image.open(path) as opened:
            if getattr(opened, "n_frames", 1) > 1:
                raise CompressionError("Imagens animadas ou com várias páginas não são aceitas; exporte um quadro primeiro.")
            opened.load()
            image = ImageOps.exif_transpose(opened)
            image.format = opened.format
            return image
    except (OSError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        raise CompressionError(f"Não foi possível abrir a imagem: {Path(path).name}. {exc}") from exc


def resized_image(image, settings):
    width, height = settings.width, settings.height
    if width is None and height is None:
        return image.copy()
    if settings.keep_ratio:
        scale = min(width / image.width if width else 1,
                    height / image.height if height else 1, 1)
        size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    else:
        size = (width or image.width, height or image.height)
    if size[0] * size[1] > Image.MAX_IMAGE_PIXELS:
        raise CompressionError("As dimensões de saída são muito grandes.")
    return image.resize(size, Image.Resampling.LANCZOS) if size != image.size else image.copy()


def _prepare(image, settings):
    notes = []
    icc = image.info.get("icc_profile")
    if image.mode == "CMYK":
        if icc:
            try:
                image = ImageCms.profileToProfile(image, ImageCms.ImageCmsProfile(BytesIO(icc)),
                                                  ImageCms.createProfile("sRGB"), outputMode="RGB")
                icc = image.info.get("icc_profile")
            except (ImageCms.PyCMSError, OSError) as exc:
                raise CompressionError(f"Não foi possível converter o perfil de cores CMYK: {exc}") from exc
        else:
            image = image.convert("RGB")
    if settings.format == "JPEG":
        if image.mode in ("RGBA", "LA", "P", "PA") or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background = Image.new("RGB", image.size, "white")
            background.paste(rgba, mask=rgba.getchannel("A"))
            image = background
            notes.append("JPEG usa fundo branco nas áreas transparentes.")
        elif image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
    elif settings.format == "WEBP":
        alpha = "A" in image.getbands() or "transparency" in image.info
        image = image.convert("RGBA" if alpha else "RGB")
    elif image.mode not in ("1", "L", "LA", "P", "RGB", "RGBA", "I", "I;16"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
    # PNG pode recuperar EXIF de image.info mesmo sem um argumento exif.
    image.info.pop("exif", None)
    image.info.pop("xmp", None)
    return image, icc, notes


def _encode(image, settings, quality, icc, cancel_event):
    _check_cancel(cancel_event)
    stream = BytesIO()
    kwargs = {"icc_profile": icc} if icc else {}
    if settings.format == "JPEG":
        kwargs.update(quality=quality, optimize=True, progressive=True,
                      subsampling=0 if quality >= 90 else 2)
    elif settings.format == "PNG":
        kwargs.update(optimize=True, compress_level=9)
        if image.mode == "P" and "transparency" in image.info:
            kwargs["transparency"] = image.info["transparency"]
    else:
        kwargs.update(quality=quality, method=6, lossless=settings.lossless, exact=True)
    image.save(stream, format=settings.format, **kwargs)
    _check_cancel(cancel_event)
    return stream.getvalue()


def _fit_target(image, settings, icc, cancel_event, progress):
    """Busca limitada: no máximo 32 resoluções e 8 qualidades por resolução."""
    target = settings.max_size_kb * 1024 if settings.max_size_kb else None
    for attempt in range(32):
        progress(min(20 + attempt * 2, 85), "Ajustando tamanho e qualidade…")
        data = _encode(image, settings, settings.quality, icc, cancel_event)
        if target is None or len(data) <= target:
            return data, image, settings.quality
        smallest = _encode(image, settings, 5, icc, cancel_event)
        if len(smallest) <= target:
            best, best_quality = smallest, 5
            low, high = 6, settings.quality - 1
            while low <= high:
                quality = (low + high) // 2
                candidate = _encode(image, settings, quality, icc, cancel_event)
                if len(candidate) <= target:
                    best, best_quality, low = candidate, quality, quality + 1
                else:
                    high = quality - 1
            return best, image, best_quality
        if image.size == (1, 1):
            break
        scale = max(0.2, min(0.85, math.sqrt(target / len(smallest)) * 0.95))
        size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        image = image.resize(size, Image.Resampling.LANCZOS)
    raise CompressionError("O limite em KB é pequeno demais. Aumente o limite; nenhuma saída foi gravada.")


def compress_image(input_path, output_path, preset="balanced", *, settings=None,
                   overwrite=False, cancel_event=None, progress=None):
    """API importável. Protege originais e publica apenas saídas completas.

    Cancelamento cooperativo entre etapas; uma codificação Pillow em andamento
    termina antes de verificar o evento. Não altera contraste ou nitidez.
    """
    started = time.monotonic()
    settings = settings or settings_for_preset(preset)
    settings.validate()
    progress = progress or (lambda percent, message: None)
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if not source.is_file():
        raise CompressionError(f"Arquivo não encontrado: {source}")
    if source == target or (target.exists() and os.path.samefile(source, target)):
        raise CompressionError("A saída deve ser diferente da imagem original.")
    valid_suffixes = {".jpg", ".jpeg"} if settings.format == "JPEG" else {EXTENSIONS[settings.format]}
    if target.suffix.lower() not in valid_suffixes:
        raise CompressionError("A extensão da saída deve corresponder ao formato escolhido.")
    if not target.parent.is_dir():
        raise CompressionError("Escolha uma pasta de destino existente.")
    if target.exists() and not overwrite:
        raise CompressionError(f"A saída já existe: {target.name}.")
    temporary = None
    try:
        _check_cancel(cancel_event)
        progress(5, "Lendo imagem…")
        original_size = source.stat().st_size
        image = load_image(source)
        original_dimensions = image.size
        original_format = image.format
        with Image.open(source) as opened:
            orientation_applied = opened.getexif().get(274) not in (None, 1)
        image = resized_image(image, settings)
        image, icc, notes = _prepare(image, settings)
        data, image, quality = _fit_target(image, settings, icc, cancel_event, progress)
        kept_original = False
        if (original_format == settings.format and image.size == original_dimensions
                and not orientation_applied and len(data) >= original_size
                and (settings.max_size_kb is None or original_size <= settings.max_size_kb * 1024)):
            data = source.read_bytes()
            kept_original = True
            notes.append("Sem redução: salva uma cópia do original, incluindo seus metadados.")
        if settings.max_size_kb and image.size != original_dimensions:
            notes.append(f"Dimensões finais para atender aos ajustes: {image.width} × {image.height} px.")
        progress(90, "Gravando resultado…")
        descriptor, name = tempfile.mkstemp(prefix=".compress-", suffix=target.suffix, dir=target.parent)
        temporary = Path(name)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        with Image.open(temporary) as check:
            check.verify()
        _check_cancel(cancel_event)
        if overwrite:
            os.replace(temporary, target)
        elif os.name == "nt":
            os.rename(temporary, target)
        else:
            os.link(temporary, target)
        return ImageCompressionResult(source, target, original_size, len(data),
                                      time.monotonic() - started, image.width, image.height,
                                      settings.format,
                                      None if kept_original or settings.format == "PNG" or settings.lossless else quality,
                                      kept_original, tuple(notes))
    except (OSError, ValueError) as exc:
        raise CompressionError(f"Não foi possível comprimir a imagem: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
