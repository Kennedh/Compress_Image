"""Fluxo real da fila e callbacks Tk; sem diálogos ou arquivos do usuário."""

from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

import customtkinter as ctk
from PIL import Image

from image_gui import ImageCompressorFrame
from image_engine import PRESETS


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            ctk.set_appearance_mode("dark")
            cls.root = ctk.CTk()
            cls.root.withdraw()
        except Exception as exc:
            raise unittest.SkipTest(f"Interface gráfica indisponível: {exc}")

    @classmethod
    def tearDownClass(cls):
        cls.root.destroy()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.source = self.folder / "photo.png"
        Image.effect_noise((160, 120), 60).convert("RGB").save(self.source)
        self.panel = ImageCompressorFrame(self.root)
        self.panel.pack(fill="both", expand=True)
        self.callback_errors = []
        self.root.report_callback_exception = lambda *args: self.callback_errors.append(args)
        self.root.update()

    def tearDown(self):
        self.panel.destroy()
        self.root.update()
        self.temp.cleanup()
        self.assertEqual(self.callback_errors, [])

    def pump_until(self, condition, timeout=10):
        deadline = time.monotonic() + timeout
        while not condition():
            if time.monotonic() >= deadline:
                self.fail("Tempo limite aguardando a interface.")
            self.root.update()
            time.sleep(0.01)
        self.root.update()

    def test_batch_continues_after_bad_file_and_renders_preview(self):
        bad = self.folder / "invalid.png"
        bad.write_bytes(b"invalid")
        self.panel.add_paths([bad, self.source, self.source])
        self.assertEqual(len(self.panel.files), 2)
        self.panel.start()
        self.assertTrue(self.panel.busy)
        self.pump_until(lambda: not self.panel.busy)
        self.assertEqual(self.panel.finished_count, 2)
        self.assertEqual(self.panel.failed_count, 1)
        item = next(row for row, path in self.panel.files.items() if path == self.source)
        result = self.panel.results[item]
        self.assertTrue(result.output_path.exists())
        self.panel.tree.selection_set(item)
        self.panel._selection_changed()
        self.pump_until(lambda: all(image is not None for image in self.panel.preview_images))
        self.assertEqual(self.panel.preview_captions[0].cget("text").split(" · ")[0], "160 × 120 px")
        self.assertEqual(self.panel.preview_captions[1].cget("text").split(" · ")[0], "160 × 120 px")

    def test_profiles_validation_and_format_controls(self):
        self.panel._profile_changed(PRESETS["web"][0])
        settings = self.panel.get_settings()
        self.assertEqual(settings.format, "WEBP")
        self.assertEqual(settings.width, 1920)
        self.panel._profile_changed(PRESETS["lossless"][0])
        self.assertEqual(self.panel.quality_slider.cget("state"), "disabled")
        self.assertEqual(self.panel.max_entry.cget("state"), "disabled")
        self.assertEqual(self.panel.get_settings().format, "PNG")
        self.panel.format.set("JPEG")
        self.panel._format_changed()
        self.assertEqual(self.panel.profile.get(), "Personalizado")
        self.assertFalse(self.panel.get_settings().lossless)
        self.panel.add_paths([self.source])
        self.panel.width.set("-1")
        with patch("image_gui.messagebox.showerror") as error:
            self.panel.start()
        error.assert_called_once()
        self.assertFalse(self.panel.busy)

    def test_automatic_names_and_source_preservation_on_repeated_runs(self):
        original = self.source.read_bytes()
        self.panel.add_paths([self.source])
        self.panel.start()
        self.pump_until(lambda: not self.panel.busy)
        first = next(iter(self.panel.results.values())).output_path
        self.panel.start()
        self.pump_until(lambda: not self.panel.busy)
        second = next(iter(self.panel.results.values())).output_path
        self.assertNotEqual(first, second)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())

    def test_cancel_stops_remaining_jobs_and_reenables_controls(self):
        for number in range(4):
            path = self.folder / f"photo{number}.png"
            Image.effect_noise((400, 300), 50).convert("RGB").save(path)
        self.panel.add_paths(sorted(self.folder.glob("*.png")))
        self.panel.start()
        self.panel.cancel()
        self.pump_until(lambda: not self.panel.busy)
        self.assertLess(len(self.panel.results), len(self.panel.files))
        self.assertIn("Cancelado", self.panel.status_label.cget("text"))
        self.assertEqual(self.panel.add_button.cget("state"), "normal")
        self.assertFalse(list(self.folder.glob(".compress-*")))

    def test_destination_and_duplicate_basenames(self):
        other = self.folder / "subfolder"
        other.mkdir()
        copy = other / self.source.name
        copy.write_bytes(self.source.read_bytes())
        self.panel.destination.set(str(self.folder))
        self.panel.add_paths([self.source, copy])
        self.panel.start()
        self.pump_until(lambda: not self.panel.busy)
        outputs = [result.output_path for result in self.panel.results.values()]
        self.assertEqual(len(set(outputs)), 2)
        self.assertTrue(all(path.parent == self.folder for path in outputs))

    def test_close_waits_for_cancellation_and_cleans_callbacks(self):
        self.panel.add_paths([self.source])
        with patch.object(self.root, "destroy") as destroy:
            self.panel.start()
            self.panel.close()
            self.assertTrue(self.panel.closing)
            self.pump_until(lambda: self.panel.disposed)
            destroy.assert_called_once()
        self.assertIsNone(self.panel.poll_id)
        self.assertIsNone(self.panel.resize_id)
        self.assertFalse(list(self.folder.glob(".compress-*")))


if __name__ == "__main__":
    unittest.main()
