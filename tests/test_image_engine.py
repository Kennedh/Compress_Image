"""Regressões do motor: arquivos reais gerados em diretórios temporários."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image, ImageChops, ImageCms

from compression_common import CompressionCancelled, CompressionError, next_output_path
from image_engine import ImageSettings, compress_image, load_image


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.source = self.folder / "original.png"
        self.image = Image.effect_noise((240, 160), 70).convert("RGB")
        self.image.save(self.source)

    def tearDown(self):
        self.temp.cleanup()

    def output(self, extension=".jpg"):
        return self.folder / ("resultado" + extension)

    def test_jpeg_and_webp_are_valid_and_preserve_source(self):
        original = self.source.read_bytes()
        for fmt, suffix in (("JPEG", ".jpg"), ("WEBP", ".webp")):
            with self.subTest(format=fmt):
                result = compress_image(self.source, self.output(suffix), settings=ImageSettings(format=fmt))
                with Image.open(result.output_path) as image:
                    image.load()
                    self.assertEqual(image.format, fmt)
                    self.assertEqual(image.size, self.image.size)
                self.assertEqual(result.compressed_size, result.output_path.stat().st_size)
                self.assertEqual(result.saved_bytes, result.original_size - result.compressed_size)
                self.assertEqual(self.source.read_bytes(), original)

    def test_png_preserves_every_pixel_and_alpha(self):
        source = self.folder / "alpha.png"
        rgba = self.image.convert("RGBA")
        rgba.putalpha(Image.linear_gradient("L").resize(rgba.size))
        rgba.save(source, compress_level=0)
        result = compress_image(source, self.output(".png"), preset="lossless")
        with Image.open(result.output_path) as image:
            self.assertIsNone(ImageChops.difference(rgba, image.convert("RGBA")).getbbox())
            self.assertEqual(rgba.tobytes(), image.convert("RGBA").tobytes())

    def test_webp_lossless_preserves_alpha_and_rgb(self):
        rgba = self.image.convert("RGBA")
        rgba.putalpha(130)
        rgba.save(self.source)
        result = compress_image(self.source, self.output(".webp"),
                                settings=ImageSettings(format="WEBP", lossless=True))
        with Image.open(result.output_path) as image:
            self.assertEqual(rgba.tobytes(), image.convert("RGBA").tobytes())

    def test_palette_transparency_is_preserved(self):
        source = self.folder / "palette.png"
        palette = Image.new("P", (20, 20), 0)
        palette.putpalette([255, 0, 0, 0, 255, 0] + [0] * 762)
        palette.putpixel((10, 10), 1)
        palette.save(source, transparency=0, compress_level=0)
        result = compress_image(source, self.output(".png"), preset="lossless")
        with Image.open(source) as before, Image.open(result.output_path) as after:
            self.assertEqual(before.convert("RGBA").tobytes(), after.convert("RGBA").tobytes())

    def test_palette_jpeg_keeps_colors_instead_of_blank_background(self):
        palette = Image.new("P", (50, 50), 0)
        palette.putpalette([255, 0, 0] + [0] * 765)
        palette.save(self.source)
        result = compress_image(self.source, self.output())
        with Image.open(result.output_path) as image:
            r, g, b = image.getpixel((25, 25))
            self.assertGreater(r, 240)
            self.assertLess(g, 15)
            self.assertLess(b, 15)

    def test_jpeg_composites_transparent_pixels_on_white(self):
        Image.new("RGBA", (50, 50), (255, 0, 0, 0)).save(self.source)
        result = compress_image(self.source, self.output())
        with Image.open(result.output_path) as image:
            self.assertEqual(image.getpixel((25, 25)), (255, 255, 255))
        self.assertTrue(result.notes)

    def test_orientation_is_applied_and_exif_is_removed(self):
        source = self.folder / "rotated.jpg"
        exif = Image.Exif()
        exif[274] = 6
        exif[315] = "private author"
        self.image.save(source, quality=95, exif=exif)
        result = compress_image(source, self.output(".png"), preset="lossless")
        with Image.open(result.output_path) as image:
            self.assertEqual(image.size, (160, 240))
            self.assertNotIn(274, image.getexif())
            self.assertNotIn(315, image.getexif())
        preview = load_image(source)
        self.assertEqual(preview.size, (160, 240))

    def test_icc_profile_is_preserved(self):
        icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        self.image.save(self.source, icc_profile=icc)
        result = compress_image(self.source, self.output())
        with Image.open(result.output_path) as image:
            self.assertEqual(image.info["icc_profile"], icc)

    def test_width_only_keeps_aspect_ratio_and_does_not_upscale(self):
        result = compress_image(self.source, self.output(), settings=ImageSettings(width=120))
        self.assertEqual((result.width, result.height), (120, 80))
        other = self.folder / "large.jpg"
        result = compress_image(self.source, other, settings=ImageSettings(width=1000))
        self.assertEqual((result.width, result.height), self.image.size)

    def test_explicit_resize_and_conversion_are_not_undone(self):
        Image.new("RGB", (2, 2), "red").save(self.source)
        result = compress_image(self.source, self.output(), settings=ImageSettings(width=50, height=30, keep_ratio=False))
        self.assertEqual((result.width, result.height), (50, 30))
        self.assertFalse(result.kept_original)
        self.assertGreater(result.compressed_size, result.original_size)
        with Image.open(result.output_path) as image:
            self.assertEqual(image.format, "JPEG")

    def test_same_format_never_grows_without_requested_transformation(self):
        Image.new("RGB", (20, 20), "red").save(self.source, optimize=True)
        result = compress_image(self.source, self.output(".png"), preset="lossless")
        self.assertLessEqual(result.compressed_size, result.original_size)
        self.assertTrue(result.kept_original)
        self.assertEqual(result.output_path.read_bytes(), self.source.read_bytes())

    def test_target_size_is_respected_for_jpeg_and_webp(self):
        for fmt, suffix in (("JPEG", ".jpg"), ("WEBP", ".webp")):
            with self.subTest(format=fmt):
                result = compress_image(self.source, self.output(suffix),
                                        settings=ImageSettings(format=fmt, max_size_kb=2))
                self.assertLessEqual(result.compressed_size, 2048)
                self.assertGreater(result.width, 0)
                with Image.open(result.output_path) as image:
                    image.load()

    def test_impossible_target_terminates_without_output(self):
        with self.assertRaisesRegex(CompressionError, "pequeno demais"):
            compress_image(self.source, self.output(), settings=ImageSettings(max_size_kb=0.001))
        self.assertFalse(self.output().exists())
        self.assertFalse(list(self.folder.glob(".compress-*")))

    def test_invalid_options_are_rejected_before_writing(self):
        cases = (dict(width=0), dict(height=-2), dict(quality=101),
                 dict(max_size_kb=float("nan")), dict(max_size_kb=float("inf")),
                 dict(max_size_kb=-1), dict(format="PNG", max_size_kb=2),
                 dict(lossless=True), dict(format="AVIF"))
        for values in cases:
            with self.subTest(values=values), self.assertRaises(CompressionError):
                compress_image(self.source, self.output(), settings=replace(ImageSettings(), **values))
        self.assertFalse(self.output().exists())

    def test_original_and_existing_output_are_protected(self):
        original = self.source.read_bytes()
        with self.assertRaises(CompressionError):
            compress_image(self.source, self.source, overwrite=True)
        self.assertEqual(self.source.read_bytes(), original)
        self.output().write_bytes(b"existing")
        with self.assertRaises(CompressionError):
            compress_image(self.source, self.output())
        self.assertEqual(self.output().read_bytes(), b"existing")
        compress_image(self.source, self.output(), overwrite=True)
        with Image.open(self.output()) as image:
            image.verify()

    def test_extension_and_missing_folder_are_rejected(self):
        with self.assertRaises(CompressionError):
            compress_image(self.source, self.output(".webp"))
        with self.assertRaises(CompressionError):
            compress_image(self.source, self.folder / "missing" / "out.jpg")

    def test_cancellation_before_and_during_processing_leaves_no_output(self):
        event = threading.Event()
        event.set()
        with self.assertRaises(CompressionCancelled):
            compress_image(self.source, self.output(), cancel_event=event)
        event.clear()
        def progress(percent, message):
            if percent >= 90:
                event.set()
        with self.assertRaises(CompressionCancelled):
            compress_image(self.source, self.output(), cancel_event=event, progress=progress)
        self.assertFalse(self.output().exists())
        self.assertFalse(list(self.folder.glob(".compress-*")))

    def test_failed_encoder_cleans_up_and_preserves_existing_target(self):
        self.output().write_bytes(b"existing")
        with patch("image_engine.Image.Image.save", side_effect=OSError("write failed")):
            with self.assertRaises(CompressionError):
                compress_image(self.source, self.output(), overwrite=True)
        self.assertEqual(self.output().read_bytes(), b"existing")
        self.assertFalse(list(self.folder.glob(".compress-*")))

    def test_collision_at_publication_does_not_overwrite(self):
        def progress(percent, message):
            if percent >= 90:
                self.output().write_bytes(b"created while processing")
        with self.assertRaises(CompressionError):
            compress_image(self.source, self.output(), progress=progress)
        self.assertEqual(self.output().read_bytes(), b"created while processing")
        self.assertFalse(list(self.folder.glob(".compress-*")))

    def test_corrupt_and_animated_inputs_are_rejected(self):
        self.source.write_bytes(b"not an image")
        with self.assertRaises(CompressionError):
            compress_image(self.source, self.output())
        frames = [Image.new("RGB", (20, 20), color) for color in ("red", "blue")]
        animated = self.folder / "animation.gif"
        frames[0].save(animated, save_all=True, append_images=frames[1:], duration=100, loop=0)
        with self.assertRaisesRegex(CompressionError, "animadas"):
            compress_image(animated, self.output())

    def test_next_name_avoids_existing_and_reserved_paths(self):
        existing = self.folder / "original_comprimido.jpg"
        existing.touch()
        reserved = {self.folder / "original_comprimido_2.jpg"}
        self.assertEqual(next_output_path(self.source, self.folder, ".jpg", reserved),
                         self.folder / "original_comprimido_3.jpg")

    def test_cli_success_and_validation(self):
        entry = Path(__file__).resolve().parents[1] / "compress_image.py"
        completed = subprocess.run([sys.executable, str(entry), str(self.source), str(self.output())],
                                   capture_output=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        invalid = subprocess.run([sys.executable, str(entry), str(self.source), str(self.output()),
                                  "--max-size-kb", "nan"], capture_output=True)
        self.assertEqual(invalid.returncode, 1)


if __name__ == "__main__":
    unittest.main()
