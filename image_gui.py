"""Interface desktop; ImageCompressorFrame pode ser incorporado a uma suíte."""

import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
from PIL import Image, ImageDraw

from compression_common import (
    CompressionCancelled, CompressionError, format_size, next_output_path,
)
from image_engine import (
    EXTENSIONS, INPUT_EXTENSIONS, PRESETS, ImageSettings,
    compress_image, load_image, settings_for_preset,
)

BG = "#0d1422"
CARD = "#162133"
SURFACE = "#1d2b40"
TEXT = "#edf3fc"
MUTED = "#99aac2"
ACCENT = "#59dfb5"


class ImageCompressorFrame(ctk.CTkFrame):
    """Painel reutilizável: recebe um master e não cria outra janela ou mainloop."""

    def __init__(self, master):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self.files = {}
        self.results = {}
        self.details = {}
        self.sizes = {}
        self.events = queue.Queue()
        self.preview_requests = queue.Queue()
        self.cancel_event = threading.Event()
        self.worker = None
        self.busy = False
        self.closing = False
        self.disposed = False
        self.poll_id = None
        self.resize_id = None
        self.preview_token = 0
        self.preview_images = (None, None)
        self.empty_preview = ctk.CTkImage(light_image=Image.new("RGBA", (1, 1)), size=(1, 1))
        self.last_output_dir = None
        self.finished_count = self.failed_count = 0
        self.saved_bytes = 0
        self.applying_profile = False
        self.profile = ctk.StringVar(value=PRESETS["balanced"][0])
        self.format = ctk.StringVar(value="JPEG")
        self.quality = ctk.IntVar(value=85)
        self.width = ctk.StringVar()
        self.height = ctk.StringVar()
        self.keep_ratio = ctk.BooleanVar(value=True)
        self.lossless = ctk.BooleanVar(value=False)
        self.max_size = ctk.StringVar()
        self.destination = ctk.StringVar()
        self.controls = []
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_header()
        self._build_stats()
        self._build_workspace()
        self._format_changed()
        for variable in (self.format, self.quality, self.width, self.height,
                         self.keep_ratio, self.lossless, self.max_size):
            variable.trace_add("write", self._settings_changed)
        self.bind("<Configure>", self._resized)
        self.poll_id = self.after(80, self._poll)
        threading.Thread(target=self._preview_worker, daemon=True).start()

    def _label(self, master, text, size=13, color=TEXT, bold=False, **kwargs):
        return ctk.CTkLabel(master, text=text, text_color=color,
                            font=ctk.CTkFont(family="Segoe UI", size=size,
                                            weight="bold" if bold else "normal"), **kwargs)

    def _button(self, master, text, command, primary=False, **kwargs):
        return ctk.CTkButton(
            master, text=text, command=command, height=kwargs.pop("height", 36), corner_radius=8,
            fg_color=ACCENT if primary else SURFACE,
            hover_color="#3cbf97" if primary else "#2a3d58",
            text_color=BG if primary else TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), **kwargs)

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 14))
        self._label(header, "COMPRESS / IMAGE", 12, ACCENT, True).pack(anchor="w")
        self._label(header, "Imagens mais leves. Mais espaço.", 26, bold=True).pack(anchor="w", pady=(4, 0))
        self._label(header, "Adicione suas imagens, escolha um perfil e compare o resultado.", color=MUTED).pack(anchor="w")

    def _build_stats(self):
        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 16))
        stats.grid_columnconfigure((0, 1, 2), weight=1)
        self.stat_labels = []
        for column, (title, value) in enumerate((
            ("NA FILA", "0 imagens"), ("TAMANHO ORIGINAL", "0 B"), ("ESPAÇO ECONOMIZADO", "0 B")
        )):
            card = ctk.CTkFrame(stats, fg_color=CARD, corner_radius=12)
            card.grid(row=0, column=column, sticky="ew", padx=(0, 12) if column < 2 else 0)
            self._label(card, title, 11, MUTED, True).pack(anchor="w", padx=16, pady=(10, 0))
            label = self._label(card, value, 23, ACCENT if column == 2 else TEXT, True)
            label.pack(anchor="w", padx=16, pady=(0, 10))
            self.stat_labels.append(label)

    def _build_workspace(self):
        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 20))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(0, weight=1)
        left = ctk.CTkFrame(workspace, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=2)
        left.grid_rowconfigure(3, weight=3)
        toolbar = ctk.CTkFrame(left, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self._label(toolbar, "01  Sua seleção", 16, bold=True).pack(side="left")
        self.add_button = self._button(toolbar, "+ Adicionar imagens", self.add_files, width=155)
        self.add_button.pack(side="right")
        self.remove_button = self._button(toolbar, "Remover", self.remove_selected, width=88)
        self.remove_button.pack(side="right", padx=8)

        table = ctk.CTkFrame(left, fg_color=CARD, corner_radius=10)
        table.grid(row=1, column=0, sticky="nsew")
        table.grid_columnconfigure(0, weight=1)
        table.grid_rowconfigure(0, weight=1)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Images.Treeview", background=CARD, foreground=TEXT,
                        fieldbackground=CARD, rowheight=34, borderwidth=0,
                        bordercolor=CARD, lightcolor=CARD, darkcolor=CARD,
                        font=("Segoe UI", 10))
        style.configure("Images.Treeview.Heading", background=SURFACE, foreground=MUTED,
                        relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Images.Treeview", background=[("selected", "#284366")],
                  foreground=[("selected", "#ffffff")])
        for orientation in ("Vertical", "Horizontal"):
            style.configure(f"Images.{orientation}.TScrollbar", background=SURFACE,
                            troughcolor=CARD, bordercolor=CARD, arrowcolor=MUTED,
                            lightcolor=SURFACE, darkcolor=SURFACE)
        self.tree = ttk.Treeview(table, style="Images.Treeview", show="headings",
                                 columns=("name", "original", "output", "reduction", "status"),
                                 selectmode="extended", height=4)
        columns = (
            ("name", "ARQUIVO", 200, 120, True),
            ("original", "ORIGINAL", 86, 75, False),
            ("output", "RESULTADO", 86, 75, False),
            ("reduction", "REDUÇÃO", 78, 70, False),
            ("status", "STATUS", 130, 100, False),
        )
        for key, title, width, minimum, stretch in columns:
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=width, minwidth=minimum, stretch=stretch)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(8, 0), pady=(8, 0))
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview,
                                  style="Images.Vertical.TScrollbar")
        scrollbar.grid(row=0, column=1, sticky="ns", pady=8)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview,
                                   style="Images.Horizontal.TScrollbar")
        horizontal.grid(row=1, column=0, sticky="ew", padx=8)
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
        self.tree.tag_configure("success", foreground=ACCENT)
        self.tree.tag_configure("error", foreground="#ffadad")
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Delete>", lambda event: self.remove_selected())
        self._label(left, "02  Compare antes e depois", 16, bold=True).grid(
            row=2, column=0, sticky="w", pady=(16, 10))

        previews = ctk.CTkFrame(left, fg_color="transparent")
        previews.grid(row=3, column=0, sticky="nsew")
        previews.grid_columnconfigure((0, 1), weight=1, uniform="preview")
        previews.grid_rowconfigure(0, weight=1)
        self.preview_labels = []
        self.preview_captions = []
        for column, title in enumerate(("ORIGINAL", "RESULTADO")):
            card = ctk.CTkFrame(previews, fg_color=CARD, corner_radius=12)
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 6) if column == 0 else (6, 0))
            card.grid_columnconfigure(0, weight=1)
            card.grid_rowconfigure(1, weight=1)
            self._label(card, title, 11, MUTED, True).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 0))
            label = self._label(card, "Selecione uma imagem" if column == 0 else "Seu resultado aparece aqui",
                                12, MUTED, wraplength=230)
            label.grid(row=1, column=0, sticky="nsew", padx=12, pady=10)
            label.bind("<Configure>", self._schedule_preview_resize)
            caption = self._label(card, "—", 11, MUTED)
            caption.grid(row=2, column=0, pady=(0, 10))
            self.preview_labels.append(label)
            self.preview_captions.append(caption)

        self.detail_label = self._label(left, "Dica: selecione uma linha para ver a imagem e os detalhes.",
                                         11, MUTED, anchor="w", justify="left", wraplength=660)
        self.detail_label.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self._build_settings(workspace)

    def _build_settings(self, workspace):
        sidebar = ctk.CTkFrame(workspace, width=325, fg_color=CARD, corner_radius=12)
        sidebar.grid(row=0, column=1, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)
        self._label(sidebar, "03  Ajuste e comprima", 17, bold=True).grid(
            row=0, column=0, sticky="w", padx=18, pady=(16, 10))
        settings = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        settings.grid(row=1, column=0, sticky="nsew", padx=8)
        settings.grid_columnconfigure(0, weight=1)
        self._label(settings, "Como você vai usar?", 13, bold=True).grid(row=0, column=0, sticky="w", padx=8)
        self.profile_menu = ctk.CTkOptionMenu(settings, variable=self.profile,
                                             values=[value[0] for value in PRESETS.values()],
                                             command=self._profile_changed, fg_color=SURFACE,
                                             button_color="#2a3d58", text_color=TEXT, height=34)
        self.profile_menu.grid(row=1, column=0, sticky="ew", padx=8, pady=(6, 0))
        self.profile_hint = self._label(settings, PRESETS["balanced"][1], 11, MUTED,
                                        wraplength=265, justify="left")
        self.profile_hint.grid(row=2, column=0, sticky="w", padx=8, pady=(6, 14))
        self._label(settings, "Formato de saída", 13, bold=True).grid(row=3, column=0, sticky="w", padx=8)
        self.format_control = ctk.CTkSegmentedButton(settings, values=list(EXTENSIONS), variable=self.format,
                                                     command=self._format_changed, height=32,
                                                     selected_color="#286e60", selected_hover_color="#338774")
        self.format_control.grid(row=4, column=0, sticky="ew", padx=8, pady=(6, 0))
        self.format_hint = self._label(settings, "", 11, MUTED, wraplength=265, justify="left")
        self.format_hint.grid(row=5, column=0, sticky="w", padx=8, pady=(6, 10))
        self.quality_label = self._label(settings, "Qualidade: 85", 12)
        self.quality_label.grid(row=6, column=0, sticky="w", padx=8)
        self.quality_slider = ctk.CTkSlider(settings, from_=5, to=100, number_of_steps=95,
                                           variable=self.quality, command=self._quality_changed,
                                           progress_color=ACCENT, button_color=ACCENT)
        self.quality_slider.grid(row=7, column=0, sticky="ew", padx=8, pady=8)
        self.lossless_switch = ctk.CTkSwitch(settings, text="WebP sem perdas", variable=self.lossless,
                                             command=self._format_changed, font=ctk.CTkFont(size=12))
        self.lossless_switch.grid(row=8, column=0, sticky="w", padx=8, pady=(2, 12))
        self._label(settings, "Dimensões (opcional)", 13, bold=True).grid(row=9, column=0, sticky="w", padx=8)
        dimensions = ctk.CTkFrame(settings, fg_color="transparent")
        dimensions.grid(row=10, column=0, sticky="ew", padx=8, pady=6)
        dimensions.grid_columnconfigure((0, 1), weight=1)
        for column, (variable, placeholder) in enumerate(((self.width, "Largura · px"), (self.height, "Altura · px"))):
            self._label(dimensions, placeholder, 11, MUTED).grid(row=0, column=column, sticky="w")
            entry = ctk.CTkEntry(dimensions, textvariable=variable, placeholder_text=placeholder, width=120)
            entry.grid(row=1, column=column, sticky="ew", padx=(0, 4) if column == 0 else (4, 0))
            self.controls.append(entry)
        self.ratio_switch = ctk.CTkCheckBox(settings, text="Manter proporção, sem ampliar",
                                            variable=self.keep_ratio, font=ctk.CTkFont(size=11),
                                            checkbox_width=18, checkbox_height=18)
        self.ratio_switch.grid(row=11, column=0, sticky="w", padx=8, pady=(3, 12))
        self._label(settings, "Limite de tamanho (KB)", 13, bold=True).grid(row=12, column=0, sticky="w", padx=8)
        self.max_entry = ctk.CTkEntry(settings, textvariable=self.max_size, placeholder_text="Sem limite")
        self.max_entry.grid(row=13, column=0, sticky="ew", padx=8, pady=(6, 0))
        self._label(settings, "Em branco: sem limite. Pode reduzir qualidade e dimensões.",
                    11, MUTED, wraplength=265, justify="left").grid(
            row=14, column=0, sticky="w", padx=8, pady=(4, 12))
        self._label(settings, "Salvar em", 13, bold=True).grid(row=15, column=0, sticky="w", padx=8)
        self.destination_entry = ctk.CTkEntry(settings, textvariable=self.destination, placeholder_text="Ao lado de cada original")
        self.destination_entry.grid(row=16, column=0, sticky="ew", padx=8, pady=6)
        self.folder_button = self._button(settings, "Escolher pasta…", self.choose_folder)
        self.folder_button.grid(row=17, column=0, sticky="ew", padx=8, pady=(0, 12))
        self._label(settings, "Em branco: salva ao lado de cada original.", 11, MUTED,
                    wraplength=265, justify="left").grid(row=18, column=0, sticky="w", padx=8, pady=(0, 12))
        self.controls.extend((self.profile_menu, self.format_control, self.quality_slider,
                              self.lossless_switch, self.ratio_switch, self.max_entry,
                              self.destination_entry, self.folder_button))
        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=18, pady=(6, 14))
        actions.grid_columnconfigure(0, weight=1)
        self.progress = ctk.CTkProgressBar(actions, height=5, progress_color=ACCENT)
        self.progress.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        self.progress.set(0)
        self.status_label = self._label(actions, "Adicione imagens para começar.", 11, MUTED,
                                        wraplength=280, justify="left")
        self.status_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        self.start_button = self._button(actions, "Comprimir imagens", self.start, primary=True, height=42)
        self.start_button.grid(row=2, column=0, sticky="ew")
        self.start_button.configure(state="disabled")
        secondary = ctk.CTkFrame(actions, fg_color="transparent")
        secondary.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        secondary.grid_columnconfigure((0, 1), weight=1)
        self.cancel_button = self._button(secondary, "Cancelar", self.cancel, width=120)
        self.cancel_button.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        self.cancel_button.configure(state="disabled")
        self.open_button = self._button(secondary, "Abrir pasta", self.open_folder, width=120)
        self.open_button.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.open_button.configure(state="disabled")

    def _profile_changed(self, title):
        self.applying_profile = True
        self.profile.set(title)
        preset = next(key for key, value in PRESETS.items() if value[0] == title)
        settings = settings_for_preset(preset)
        self.profile_hint.configure(text=PRESETS[preset][1])
        self.format.set(settings.format)
        self.quality.set(settings.quality)
        self.width.set(str(settings.width) if settings.width else "")
        self.height.set(str(settings.height) if settings.height else "")
        self.keep_ratio.set(settings.keep_ratio)
        self.lossless.set(settings.lossless)
        self.max_size.set("")
        self._format_changed()
        self.applying_profile = False

    def _settings_changed(self, *args):
        if not self.applying_profile:
            self.profile.set("Personalizado")
            self.profile_hint.configure(text="Ajustes personalizados. A compressão usa os valores abaixo.")

    def _quality_changed(self, value=None):
        self.quality_label.configure(text=f"Qualidade: {self.quality.get()}")

    def _format_changed(self, value=None):
        fmt = self.format.get()
        if fmt != "WEBP" and self.lossless.get() != (fmt == "PNG"):
            self.lossless.set(fmt == "PNG")
        self.format_hint.configure(text={
            "JPEG": "Para fotos. Transparência recebe fundo branco.",
            "PNG": "Preserva cores e transparência, sem quantização.",
            "WEBP": "Arquivos leves com suporte a transparência.",
        }[fmt])
        self.lossless_switch.configure(state="normal" if fmt == "WEBP" and not self.busy else "disabled")
        lossy = fmt != "PNG" and not self.lossless.get()
        self.quality_slider.configure(state="normal" if lossy and not self.busy else "disabled")
        self.quality_label.configure(text=f"Qualidade: {self.quality.get()}" if lossy else "Compressão sem perdas")
        self.max_entry.configure(state="normal" if lossy and not self.busy else "disabled")
        if not lossy and self.max_size.get():
            self.max_size.set("")

    def add_files(self):
        if self.busy:
            return
        paths = filedialog.askopenfilenames(parent=self.winfo_toplevel(), title="Adicionar imagens",
                                            filetypes=[("Imagens", INPUT_EXTENSIONS), ("Todos os arquivos", "*.*")])
        self.add_paths(paths)

    def add_paths(self, paths):
        """Adiciona caminhos sem abrir diálogos; útil também para futura integração."""
        if self.busy:
            return
        errors = []
        for filename in paths:
            path = Path(filename).expanduser().resolve()
            if path in self.files.values():
                continue
            try:
                if not path.is_file():
                    raise OSError("Arquivo não encontrado.")
                size = path.stat().st_size
                item = self.tree.insert("", "end", values=(path.name, format_size(size), "—", "—", "Na fila"))
                self.files[item] = path
                self.sizes[item] = size
                self.details[item] = str(path)
            except OSError as exc:
                errors.append(f"{path.name}: {exc}")
        self._refresh()
        if self.files and not self.tree.selection():
            self.tree.selection_set(next(iter(self.files)))
        if errors:
            messagebox.showwarning("Arquivos não adicionados", "\n".join(errors), parent=self.winfo_toplevel())

    def remove_selected(self):
        if self.busy:
            return
        for item in self.tree.selection():
            self.tree.delete(item)
            for mapping in (self.files, self.results, self.details, self.sizes):
                mapping.pop(item, None)
        self._refresh()
        self._selection_changed()

    def _refresh(self):
        count = len(self.files)
        self.stat_labels[0].configure(text=f"{count} imagem" if count == 1 else f"{count} imagens")
        self.stat_labels[1].configure(text=format_size(sum(self.sizes.values())))
        self.start_button.configure(state="normal" if count and not self.busy else "disabled")

    def choose_folder(self):
        folder = filedialog.askdirectory(parent=self.winfo_toplevel(), title="Pasta das imagens comprimidas")
        if folder:
            self.destination.set(folder)

    def get_settings(self):
        try:
            settings = ImageSettings(
                format=self.format.get(), quality=self.quality.get(),
                width=int(self.width.get()) if self.width.get().strip() else None,
                height=int(self.height.get()) if self.height.get().strip() else None,
                keep_ratio=self.keep_ratio.get(),
                max_size_kb=float(self.max_size.get().replace(",", ".")) if self.max_size.get().strip() else None,
                lossless=self.lossless.get(),
            )
        except ValueError as exc:
            raise CompressionError("Preencha dimensões com inteiros e limite em KB com um número.") from exc
        settings.validate()
        return settings

    def _set_busy(self, busy):
        self.busy = busy
        for widget in (*self.controls, self.add_button, self.remove_button):
            widget.configure(state="disabled" if busy else "normal")
        self.cancel_button.configure(state="normal" if busy else "disabled")
        self.start_button.configure(state="disabled" if busy or not self.files else "normal")
        self.start_button.configure(text="Comprimindo…" if busy else "Comprimir imagens")
        if not busy:
            self._format_changed()

    def start(self):
        if self.busy or not self.files:
            return
        try:
            settings = self.get_settings()
            folder = Path(self.destination.get().strip()).expanduser().resolve() if self.destination.get().strip() else None
            if folder is not None and not folder.is_dir():
                raise CompressionError("Escolha uma pasta de destino existente.")
            jobs = []
            reserved = set(self.files.values())
            for item, source in self.files.items():
                target = next_output_path(source, folder or source.parent, EXTENSIONS[settings.format], reserved)
                reserved.add(target)
                jobs.append((item, source, target))
        except (CompressionError, OSError) as exc:
            messagebox.showerror("Confira os ajustes", str(exc), parent=self.winfo_toplevel())
            return
        for item, source, target in jobs:
            self.tree.item(item, tags=())
            self.tree.set(item, "status", "Na fila")
            self.tree.set(item, "output", "—")
            self.tree.set(item, "reduction", "—")
            self.details[item] = f"Original: {source}\nDestino: {target}"
        self.results.clear()
        self._selection_changed()
        self.finished_count = self.failed_count = self.saved_bytes = 0
        self.stat_labels[2].configure(text=format_size(0))
        self.progress.set(0)
        self.cancel_event.clear()
        self._set_busy(True)
        self.worker = threading.Thread(target=self._process, args=(jobs, settings), daemon=True)
        self.worker.start()

    def _process(self, jobs, settings):
        try:
            for index, (item, source, target) in enumerate(jobs):
                if self.cancel_event.is_set():
                    break
                self.events.put(("started", item, source.name))
                try:
                    result = compress_image(
                        source, target, settings=settings, cancel_event=self.cancel_event,
                        progress=lambda pct, msg, row=item, position=index: self.events.put(
                            ("progress", row, ((position + pct / 100) / len(jobs), msg))))
                    self.events.put(("result", item, result))
                except CompressionCancelled:
                    break
                except (CompressionError, OSError) as exc:
                    self.events.put(("error", item, str(exc)))
        except Exception as exc:
            self.events.put(("unexpected", None, str(exc)))
        finally:
            self.events.put(("done", None, self.cancel_event.is_set()))

    def _poll(self):
        self.poll_id = None
        try:
            while True:
                event, item, value = self.events.get_nowait()
                if event == "preview":
                    if item == self.preview_token:
                        self.preview_images, captions, error = value
                        for label, caption in zip(self.preview_captions, captions):
                            label.configure(text=caption)
                        self._render_previews()
                        if error:
                            self.detail_label.configure(text=error)
                    continue
                if event == "started":
                    self.tree.set(item, "status", "Comprimindo…")
                    self.status_label.configure(text=f"{self.finished_count + 1}/{len(self.files)} · {value}")
                elif event == "progress":
                    self.progress.set(value[0])
                elif event == "result":
                    self.finished_count += 1
                    self.results[item] = value
                    self.saved_bytes += value.saved_bytes
                    self.tree.set(item, "output", format_size(value.compressed_size))
                    self.tree.set(item, "reduction", f"{value.reduction_percent:.1f}%".replace(".", ","))
                    status = "Sem redução" if value.kept_original else ("Arquivo maior" if value.saved_bytes < 0 else "Concluído")
                    self.tree.set(item, "status", status)
                    self.tree.item(item, tags=("success",) if value.saved_bytes >= 0 else ())
                    self.details[item] = (f"Salvo em: {value.output_path}\n"
                                          f"{value.width} × {value.height} px · {value.elapsed_seconds:.1f}s"
                                          + ("\n" + " ".join(value.notes) if value.notes else ""))
                    self.last_output_dir = value.output_path.parent
                    self.open_button.configure(state="normal")
                    self.stat_labels[2].configure(text=format_size(self.saved_bytes))
                    self.progress.set(self.finished_count / len(self.files))
                elif event == "error":
                    self.finished_count += 1
                    self.failed_count += 1
                    self.tree.set(item, "status", "Erro · veja detalhes")
                    self.tree.item(item, tags=("error",))
                    self.details[item] = value
                    self.progress.set(self.finished_count / len(self.files))
                elif event == "unexpected":
                    self.failed_count += 1
                    self.detail_label.configure(text=f"Falha inesperada: {value}")
                elif event == "done":
                    for row in self.files:
                        if self.tree.set(row, "status") in ("Na fila", "Comprimindo…"):
                            self.tree.set(row, "status", "Cancelado" if value else "Não processado")
                    self._set_busy(False)
                    successes = max(0, self.finished_count - self.failed_count)
                    self.status_label.configure(text=(
                        f"{'Cancelado' if value else 'Finalizado'} · {successes} concluída(s)"
                        f" · {self.failed_count} erro(s)."))
                    if self.closing:
                        self._destroy()
                        self.winfo_toplevel().destroy()
                        return
                if event in ("result", "error") and item in self.tree.selection():
                    self._selection_changed()
        except queue.Empty:
            pass
        self.poll_id = self.after(80, self._poll)

    def _selection_changed(self, event=None):
        selected = self.tree.selection()
        self.preview_token += 1
        self.preview_images = (None, None)
        self._render_previews()
        for label in self.preview_captions:
            label.configure(text="—")
        if not selected:
            self.detail_label.configure(text="Selecione uma linha para comparar as imagens.")
            return
        item = selected[0]
        self.detail_label.configure(text=self.details.get(item, ""))
        source = self.files[item]
        result = self.results.get(item)
        self.preview_requests.put((self.preview_token, source, result.output_path if result else None))

    def _preview_worker(self):
        while True:
            request = self.preview_requests.get()
            while not self.preview_requests.empty():
                request = self.preview_requests.get()
            if request is None:
                return
            token, source, output = request
            images, captions, errors = [], [], []
            for path in (source, output):
                image = None
                caption = "—"
                if path:
                    try:
                        image = load_image(path)
                        caption = f"{image.width} × {image.height} px · {format_size(path.stat().st_size)}"
                        image.thumbnail((1200, 800), Image.Resampling.LANCZOS)
                        image = image.convert("RGBA")
                    except (CompressionError, OSError, ValueError) as exc:
                        errors.append(str(exc))
                images.append(image)
                captions.append(caption)
            self.events.put(("preview", token, (tuple(images), captions, "\n".join(errors))))

    def _render_previews(self):
        for index, (label, original) in enumerate(zip(self.preview_labels, self.preview_images)):
            if original is None:
                # CTkLabel 5.2 não limpa a imagem Tk ao receber image=None.
                label.configure(image=self.empty_preview, text="Selecione uma imagem" if index == 0 else "Seu resultado aparece aqui")
                label.preview_image = None
                continue
            image = original.copy()
            width, height = max(40, label.winfo_width() - 16), max(40, label.winfo_height() - 16)
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
            # Xadrez revela transparência sem modificar a imagem exportada.
            background = Image.new("RGBA", image.size, "#dce1e8")
            draw = ImageDraw.Draw(background)
            for y in range(0, image.height, 12):
                for x in range(0, image.width, 12):
                    if (x // 12 + y // 12) % 2:
                        draw.rectangle((x, y, x + 11, y + 11), fill="#b9c3d1")
            background.alpha_composite(image)
            preview = ctk.CTkImage(light_image=background, dark_image=background, size=image.size)
            label.configure(image=preview, text="")
            label.preview_image = preview

    def _resized(self, event):
        if event.widget != self:
            return
        self._schedule_preview_resize(event)

    def _schedule_preview_resize(self, event=None):
        if self.disposed:
            return
        if self.resize_id is not None:
            self.after_cancel(self.resize_id)
        self.resize_id = self.after(150, self._render_after_resize)

    def _render_after_resize(self):
        self.resize_id = None
        self._render_previews()

    def cancel(self):
        if self.busy:
            self.cancel_event.set()
            self.cancel_button.configure(state="disabled")
            self.status_label.configure(text="Cancelando após a etapa atual…")

    def open_folder(self):
        if self.last_output_dir is None:
            return
        try:
            if os.name == "nt":
                os.startfile(self.last_output_dir)
            else:
                subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(self.last_output_dir)])
        except OSError as exc:
            messagebox.showerror("Não foi possível abrir a pasta", str(exc), parent=self.winfo_toplevel())

    def _destroy(self):
        if self.disposed:
            return
        self.disposed = True
        self.preview_requests.put(None)
        for identifier in (self.poll_id, self.resize_id):
            if identifier is not None:
                self.after_cancel(identifier)
        self.poll_id = self.resize_id = None

    def destroy(self):
        self.cancel_event.set()
        self._destroy()
        super().destroy()

    def close(self):
        if self.busy:
            self.closing = True
            self.cancel()
        else:
            self._destroy()
            self.winfo_toplevel().destroy()


class ImageCompressor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Compress Image")
        self.geometry("1280x880")
        self.minsize(1060, 760)
        self.configure(fg_color=BG)
        self.panel = ImageCompressorFrame(self)
        self.panel.pack(fill="both", expand=True)
        self.protocol("WM_DELETE_WINDOW", self.panel.close)
        self.bind("<Control-o>", lambda event: self.panel.add_files())


def launch():
    ctk.set_appearance_mode("dark")
    app = ImageCompressor()
    app.mainloop()


if __name__ == "__main__":
    launch()
