"""
Compressor de Imagem Pro - Versão Final Otimizada
==================================================
- Compressão inteligente com preservação de qualidade
- JPEG: .jpg e .jpeg, chroma subsampling adaptativo
- PNG: .png, quantização inteligente
- WEBP: .webp, lossless/lossy automático
- Redimensionamento com ou sem proporção
- Preview em tempo real
"""

import sys
import os
from pathlib import Path
from PIL import Image, ImageFilter, ImageEnhance
import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import platform

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class CompressionThread(threading.Thread):
    def __init__(self, input_path, output_path, settings, callback):
        super().__init__()
        self.input_path = input_path
        self.output_path = output_path
        self.settings = settings
        self.callback = callback
        self.daemon = True

    def run(self):
        try:
            img = Image.open(self.input_path)
            original_size = os.path.getsize(self.input_path) / 1024
            original_w, original_h = img.width, img.height

            self.callback("progress", 5, "Analisando imagem...")

            has_transparency = self._detect_transparency(img)
            num_colors = self._count_colors(img)
            is_photo = img.mode in ('RGB', 'RGBA') and num_colors > 1000

            # ===== REDIMENSIONAMENTO =====
            self.callback("progress", 15, "Redimensionando...")

            target_w = self.settings['width'] or img.width
            target_h = self.settings['height'] or img.height

            if self.settings['keep_ratio']:
                # Mantém proporção (thumbnail)
                img.thumbnail((target_w, target_h), Image.LANCZOS)
            else:
                # Força dimensões exatas (esticar)
                img = img.resize((target_w, target_h), Image.LANCZOS)

            # Sharpen se reduziu muito
            if img.width < original_w * 0.5:
                img = img.filter(ImageFilter.SHARPEN)

            # ===== OTIMIZAÇÃO FOTOGRÁFICA =====
            if is_photo and self.settings['format'] in ('JPEG', 'WEBP'):
                # Aplica pequenas melhorias em fotos
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(1.05)  # +5% nitidez

                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(1.02)  # +2% contraste

            # ===== COMPRESSÃO =====
            self.callback("progress", 30, "Comprimindo...")

            output_format = self.settings['format']
            quality = self.settings['quality']

            if output_format == 'JPEG':
                final_quality = self._compress_jpeg(img, quality,
                                                    self.settings['max_size_kb'], is_photo, has_transparency)
            elif output_format == 'PNG':
                final_quality = self._compress_png(img, num_colors, has_transparency)
            elif output_format == 'WEBP':
                final_quality = self._compress_webp(img, quality, has_transparency)

            self.callback("progress", 95, "Finalizando...")
            final_size = os.path.getsize(self.output_path) / 1024
            self.callback("finished", self.output_path, final_size, final_quality, original_size)

        except Exception as e:
            self.callback("error", str(e))

    def _detect_transparency(self, img):
        if img.mode == 'RGBA':
            return img.split()[3].getextrema()[0] < 255
        elif img.mode == 'LA':
            return img.split()[1].getextrema()[0] < 255
        elif img.mode == 'P':
            return 'transparency' in img.info
        return False

    def _count_colors(self, img):
        if img.mode in ('RGB', 'RGBA'):
            if img.width * img.height > 500000:
                sample = img.resize((200, 200), Image.NEAREST)
                colors = sample.getcolors(maxcolors=50000)
            else:
                colors = img.getcolors(maxcolors=100000)
            return len(colors) if colors else 100000
        elif img.mode == 'P':
            colors = img.getcolors()
            return len(colors) if colors else 256
        return 256

    def _compress_jpeg(self, img, quality, max_size_kb, is_photo, has_transparency):
        """Compressão JPEG de alta qualidade"""
        # Trata transparência
        if has_transparency or img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[3])
            elif img.mode == 'LA':
                bg.paste(img, mask=img.split()[1])
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Configurações otimizadas para qualidade
        kwargs = {
            'format': 'JPEG',
            'optimize': True,
            'progressive': True,
            'subsampling': '4:4:4' if quality >= 70 else '4:2:0',
            'quantization': None,  # Usa tabelas padrão otimizadas
        }

        if max_size_kb:
            q = quality
            min_q = 5
            orig_w, orig_h = img.width, img.height
            step = 0

            while True:
                kwargs['quality'] = q
                img.save(self.output_path, **kwargs)
                size_kb = os.path.getsize(self.output_path) / 1024

                if size_kb <= max_size_kb:
                    break

                if q <= min_q:
                    step += 1
                    scale = max(0.1, 1.0 - step * 0.1)
                    if scale < 0.1:
                        self.callback("progress", 90, f"⚠️ Mínimo: {size_kb:.1f}KB")
                        break

                    new_w = int(orig_w * scale)
                    new_h = int(orig_h * scale)
                    img_resized = img.resize((new_w, new_h), Image.LANCZOS)

                    self.callback("progress", 60 + step * 3, f"Reduzindo: {new_w}×{new_h}px")

                    kwargs['quality'] = min_q
                    img_resized.save(self.output_path, **kwargs)
                    size_kb = os.path.getsize(self.output_path) / 1024

                    if size_kb <= max_size_kb:
                        break
                    continue

                # Redução gradual
                if q > 80:
                    q -= 1
                elif q > 50:
                    q -= 2
                elif q > 20:
                    q -= 3
                else:
                    q -= 5
                q = max(q, min_q)

                progress = 30 + int((quality - q) / quality * 60)
                self.callback("progress", min(progress, 90), f"Qualidade: {q}%")

            return max(q, min_q)
        else:
            kwargs['quality'] = quality
            img.save(self.output_path, **kwargs)
            return quality

    def _compress_png(self, img, num_colors, has_transparency):
        """Compressão PNG inteligente - NÃO AUMENTA o tamanho"""
        original_mode = img.mode

        if has_transparency:
            # PNG com transparência
            if num_colors <= 256:
                # Poucas cores: usa paleta
                img = img.convert('P', palette=Image.ADAPTIVE, colors=max(16, num_colors))
                img.save(self.output_path, 'PNG', optimize=True)
            else:
                # Muitas cores: mantém RGBA com compressão máxima
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                img.save(self.output_path, 'PNG', optimize=True, compress_level=9)
        else:
            # PNG sem transparência
            if num_colors <= 256:
                # Poucas cores: paleta
                img = img.convert('P', palette=Image.ADAPTIVE, colors=max(16, num_colors))
                img.save(self.output_path, 'PNG', optimize=True)
            elif num_colors <= 65536:
                # Cores moderadas: tenta paleta primeiro
                img_p = img.convert('P', palette=Image.ADAPTIVE, colors=256)

                # Salva as duas versões e compara
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                    tmp_path = tmp.name

                img_p.save(tmp_path, 'PNG', optimize=True)
                size_palette = os.path.getsize(tmp_path)

                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(self.output_path, 'PNG', optimize=True, compress_level=9)
                size_rgb = os.path.getsize(self.output_path)

                # Usa a menor versão
                if size_palette < size_rgb:
                    img_p.save(self.output_path, 'PNG', optimize=True)

                os.unlink(tmp_path)
            else:
                # Muitas cores: RGB com compressão máxima
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(self.output_path, 'PNG', optimize=True, compress_level=9)

        return 0

    def _compress_webp(self, img, quality, has_transparency):
        """Compressão WEBP otimizada - NÃO AUMENTA o tamanho"""
        if has_transparency:
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
        else:
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

        # Tenta lossless e lossy, usa o menor
        import tempfile

        # Versão lossy
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp:
            tmp_lossy = tmp.name

        img.save(tmp_lossy, 'WEBP', quality=quality, method=6, lossless=False)
        size_lossy = os.path.getsize(tmp_lossy)

        # Versão lossless
        with tempfile.NamedTemporaryFile(suffix='.webp', delete=False) as tmp:
            tmp_lossless = tmp.name

        img.save(tmp_lossless, 'WEBP', lossless=True, quality=100, method=6)
        size_lossless = os.path.getsize(tmp_lossless)

        # Usa a menor versão
        if size_lossy <= size_lossless:
            img.save(self.output_path, 'WEBP', quality=quality, method=6, lossless=False)
        else:
            img.save(self.output_path, 'WEBP', lossless=True, quality=100, method=6)

        os.unlink(tmp_lossy)
        os.unlink(tmp_lossless)

        return quality if size_lossy <= size_lossless else 100


class ScrollFrame(ctk.CTkScrollableFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.bind("<MouseWheel>", self._scroll)
        self.bind("<Button-4>", self._scroll)
        self.bind("<Button-5>", self._scroll)

    def _scroll(self, event):
        if platform.system() == 'Linux':
            if event.num == 4:
                self._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                self._parent_canvas.yview_scroll(1, "units")
        else:
            self._parent_canvas.yview_scroll(-event.delta // 120, "units")


class ImageCompressor(ctk.CTk):
    FORMATOS_ENTRADA = """
    • JPEG (.jpg, .jpeg)  • PNG (.png)
    • BMP (.bmp)          • GIF (.gif)
    • TIFF (.tiff, .tif)  • WEBP (.webp)
    • ICO (.ico)          • PPM, PGM, PCX, TGA
    """

    def __init__(self):
        super().__init__()

        self.title("Compressor de Imagem Pro")
        self.geometry("1200x750")
        self.minsize(900, 550)

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 1200) // 2
        y = (self.winfo_screenheight() - 750) // 2
        self.geometry(f"+{x}+{y}")

        self.caminho_imagem = None
        self.imagem_original = None
        self.imagem_preview = None

        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=4)
        self.grid_rowconfigure(0, weight=1)

        self._criar_painel_preview()
        self._criar_painel_controles()
        self.bind("<Configure>", self._ao_redimensionar)

    def _criar_painel_preview(self):
        painel = ctk.CTkFrame(self, fg_color="transparent")
        painel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        painel.grid_columnconfigure(0, weight=1)
        painel.grid_rowconfigure(1, weight=1)

        barra = ctk.CTkFrame(painel, fg_color="transparent")
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(barra, text="🖼️ Visualização", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")

        self.btn_abrir = ctk.CTkButton(
            barra, text="📂 Abrir Imagem", command=self._abrir_imagem,
            width=120, height=32, font=ctk.CTkFont(size=13),
            corner_radius=8, fg_color="#4CAF50", hover_color="#45a049"
        )
        self.btn_abrir.pack(side="right")

        self.frame_preview = ctk.CTkFrame(painel, fg_color=("gray95", "gray17"), corner_radius=12)
        self.frame_preview.grid(row=1, column=0, sticky="nsew")
        self.frame_preview.grid_columnconfigure(0, weight=1)
        self.frame_preview.grid_rowconfigure(0, weight=1)

        self.label_preview = ctk.CTkLabel(
            self.frame_preview,
            text="Nenhuma imagem carregada\n\nClique em 'Abrir Imagem'",
            font=ctk.CTkFont(size=14), text_color="gray50", anchor="center"
        )
        self.label_preview.grid(row=0, column=0, sticky="nsew")

        self.label_info = ctk.CTkLabel(painel, text="Pronto", font=ctk.CTkFont(size=12), text_color="gray60")
        self.label_info.grid(row=2, column=0, pady=(10, 0), sticky="w")

    def _criar_painel_controles(self):
        painel = ctk.CTkFrame(self, corner_radius=12)
        painel.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        painel.grid_columnconfigure(0, weight=1)
        painel.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(painel, text="⚙️ Ferramentas", font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        self.scroll = ScrollFrame(painel)
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self._secao_dimensoes()
        self._secao_formato()
        self._secao_qualidade()
        self._secao_tamanho()
        self._secao_comprimir()
        self._secao_resultados()

        # Atualiza preview quando mudar dimensões
        self.var_largura.trace_add("write", lambda *a: self._preview_com_dimensoes())
        self.var_altura.trace_add("write", lambda *a: self._preview_com_dimensoes())
        self.var_proporcao.trace_add("write", lambda *a: self._preview_com_dimensoes())

    def _secao_dimensoes(self):
        frame = ctk.CTkFrame(self.scroll, corner_radius=10)
        frame.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="📐 Dimensões", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        self.var_proporcao = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            frame, text="Manter proporção", variable=self.var_proporcao,
            font=ctk.CTkFont(size=12), checkbox_width=22, checkbox_height=22
        ).grid(row=1, column=0, padx=15, pady=5, sticky="w")

        grid = ctk.CTkFrame(frame, fg_color="transparent")
        grid.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        grid.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(grid, text="Largura (px)", font=ctk.CTkFont(size=11)).grid(row=0, column=0)
        self.var_largura = ctk.StringVar()
        self.entrada_largura = ctk.CTkEntry(
            grid, textvariable=self.var_largura, placeholder_text="Auto",
            height=34, corner_radius=6
        )
        self.entrada_largura.grid(row=1, column=0, padx=(0, 5), pady=(5, 0), sticky="ew")

        ctk.CTkLabel(grid, text="Altura (px)", font=ctk.CTkFont(size=11)).grid(row=0, column=1)
        self.var_altura = ctk.StringVar()
        self.entrada_altura = ctk.CTkEntry(
            grid, textvariable=self.var_altura, placeholder_text="Auto",
            height=34, corner_radius=6
        )
        self.entrada_altura.grid(row=1, column=1, padx=(5, 0), pady=(5, 0), sticky="ew")

        botoes = ctk.CTkFrame(frame, fg_color="transparent")
        botoes.grid(row=3, column=0, padx=15, pady=(5, 15), sticky="ew")
        ctk.CTkLabel(botoes, text="Rápido:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 10))

        for txt, esc in [("50%", 0.5), ("75%", 0.75), ("100%", 1.0)]:
            ctk.CTkButton(botoes, text=txt, width=50, height=28, font=ctk.CTkFont(size=11),
                          corner_radius=6, command=lambda e=esc: self._redimensionar_rapido(e)
                          ).pack(side="left", padx=2)

    def _secao_formato(self):
        frame = ctk.CTkFrame(self.scroll, corner_radius=10)
        frame.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="🎯 Formato", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        self.var_formato = ctk.StringVar(value="JPEG")

        for i, (fmt, desc) in enumerate([
            ("JPEG", "Fotos - menor tamanho (.jpg)"),
            ("PNG", "Transparência - sem perdas (.png)"),
            ("WEBP", "Moderno - melhor compressão (.webp)")
        ]):
            linha = ctk.CTkFrame(frame, fg_color="transparent")
            linha.grid(row=i + 1, column=0, padx=15, pady=3, sticky="ew")
            ctk.CTkRadioButton(linha, text=fmt, variable=self.var_formato, value=fmt,
                               font=ctk.CTkFont(size=13, weight="bold"), command=self._ao_mudar_formato
                               ).pack(side="left")
            ctk.CTkLabel(linha, text=desc, font=ctk.CTkFont(size=11), text_color="gray60").pack(side="right")

    def _secao_qualidade(self):
        self.frame_qualidade = ctk.CTkFrame(self.scroll, corner_radius=10)
        self.frame_qualidade.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        self.frame_qualidade.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.frame_qualidade, text="✨ Qualidade", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        self.label_qualidade = ctk.CTkLabel(self.frame_qualidade, text="Qualidade: 85%", font=ctk.CTkFont(size=12))
        self.label_qualidade.grid(row=1, column=0, padx=15, sticky="w")

        self.var_qualidade = ctk.IntVar(value=85)
        self.slider_qualidade = ctk.CTkSlider(
            self.frame_qualidade, from_=5, to=100, variable=self.var_qualidade,
            command=lambda v: self.label_qualidade.configure(text=f"Qualidade: {int(v)}%"),
            height=20, corner_radius=6
        )
        self.slider_qualidade.grid(row=2, column=0, padx=15, pady=(8, 15), sticky="ew")

        ctk.CTkLabel(self.frame_qualidade, text="← Menor arquivo | Maior qualidade →",
                     font=ctk.CTkFont(size=10), text_color="gray60"
                     ).grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")

    def _secao_tamanho(self):
        frame = ctk.CTkFrame(self.scroll, corner_radius=10)
        frame.grid(row=3, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="📏 Limite (JPEG)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 10), sticky="w")

        linha = ctk.CTkFrame(frame, fg_color="transparent")
        linha.grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        ctk.CTkLabel(linha, text="Máximo:", font=ctk.CTkFont(size=12)).pack(side="left")

        self.var_tamanho = ctk.StringVar()
        self.entrada_tamanho = ctk.CTkEntry(
            linha, textvariable=self.var_tamanho, placeholder_text="Ilimitado",
            width=100, height=32, corner_radius=6
        )
        self.entrada_tamanho.pack(side="right")
        ctk.CTkLabel(linha, text="KB", font=ctk.CTkFont(size=12)).pack(side="right", padx=5)

    def _secao_comprimir(self):
        frame = ctk.CTkFrame(self.scroll, corner_radius=10)
        frame.grid(row=4, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        self.btn_comprimir = ctk.CTkButton(
            frame, text="🚀 Comprimir Imagem", command=self._comprimir_imagem,
            height=50, font=ctk.CTkFont(size=16, weight="bold"),
            corner_radius=10, state="disabled",
            fg_color="#2196F3", hover_color="#1976D2"
        )
        self.btn_comprimir.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        self.label_progresso = ctk.CTkLabel(frame, text="", font=ctk.CTkFont(size=11), text_color="gray60")
        self.label_progresso.grid(row=1, column=0, padx=15, pady=(5, 0))

        self.barra_progresso = ctk.CTkProgressBar(frame)
        self.barra_progresso.grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        self.barra_progresso.set(0)
        self.barra_progresso.grid_remove()

    def _secao_resultados(self):
        frame = ctk.CTkFrame(self.scroll, corner_radius=10)
        frame.grid(row=5, column=0, padx=5, pady=5, sticky="ew")
        frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame, text="📋 Resultado", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, padx=15, pady=(15, 5), sticky="w")

        self.texto_resultado = ctk.CTkTextbox(frame, height=120, font=ctk.CTkFont(size=11),
                                              wrap="word", corner_radius=8)
        self.texto_resultado.grid(row=1, column=0, padx=15, pady=(5, 15), sticky="ew")
        self.texto_resultado.insert("1.0", "Aguardando imagem...")
        self.texto_resultado.configure(state="disabled")

    def _redimensionar_rapido(self, escala):
        if self.imagem_original:
            w = int(self.imagem_original.width * escala)
            h = int(self.imagem_original.height * escala)
            self.var_largura.set(str(w))
            self.var_altura.set(str(h))

    def _ao_mudar_formato(self):
        if self.var_formato.get() in ('JPEG', 'WEBP'):
            self.frame_qualidade.grid()
        else:
            self.frame_qualidade.grid_remove()

    def _preview_com_dimensoes(self):
        """Atualiza preview com as dimensões digitadas"""
        if self.imagem_original and self.var_largura.get() and self.var_altura.get():
            try:
                w = int(self.var_largura.get())
                h = int(self.var_altura.get())

                img = self.imagem_original.copy()

                if self.var_proporcao.get():
                    img.thumbnail((w, h), Image.LANCZOS)
                else:
                    img = img.resize((w, h), Image.LANCZOS)

                self.imagem_preview = img
                self._atualizar_preview()
            except ValueError:
                pass

    def _abrir_imagem(self):
        caminho = filedialog.askopenfilename(title="Selecionar Imagem")
        if caminho:
            self._carregar_imagem(caminho)

    def _carregar_imagem(self, caminho):
        try:
            try:
                img = Image.open(caminho)
                img.verify()
                img = Image.open(caminho)
            except Exception:
                messagebox.showerror("Arquivo não suportado",
                                     f"❌ Não foi possível abrir:\n{os.path.basename(caminho)}\n\n"
                                     f"📋 Formatos aceitos:\n{self.FORMATOS_ENTRADA}")
                return

            self.caminho_imagem = caminho
            self.imagem_original = img.copy()
            self.imagem_preview = img.copy()

            tamanho_kb = os.path.getsize(caminho) / 1024
            self.label_info.configure(text=f"📄 {img.format} | 📏 {img.width}×{img.height}px | 💾 {tamanho_kb:.1f}KB")

            self.var_largura.set(str(img.width))
            self.var_altura.set(str(img.height))

            self._atualizar_preview()
            self.btn_comprimir.configure(state="normal")

            self.texto_resultado.configure(state="normal")
            self.texto_resultado.delete("1.0", "end")
            self.texto_resultado.insert("1.0",
                                        f"✅ {os.path.basename(caminho)}\n"
                                        f"Formato: {img.format} | Modo: {img.mode}\n"
                                        f"Dimensões: {img.width}×{img.height}px\n"
                                        f"Tamanho: {tamanho_kb:.1f} KB")
            self.texto_resultado.configure(state="disabled")

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao abrir:\n{str(e)}")

    def _atualizar_preview(self):
        if self.imagem_preview:
            self.update_idletasks()
            pw = self.frame_preview.winfo_width() - 30
            ph = self.frame_preview.winfo_height() - 30

            if pw > 50 and ph > 50:
                img = self.imagem_preview.copy()

                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGBA')
                    bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.thumbnail((pw, ph), Image.LANCZOS)

                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(img.width, img.height))
                self.label_preview.configure(image=ctk_img, text="")

    def _ao_redimensionar(self, event):
        if event.widget == self and self.imagem_preview:
            self.after(150, self._atualizar_preview)

    def _comprimir_imagem(self):
        if not self.caminho_imagem:
            messagebox.showwarning("Aviso", "Abra uma imagem primeiro!")
            return

        formato = self.var_formato.get()
        extensoes = {'JPEG': '.jpg', 'PNG': '.png', 'WEBP': '.webp'}
        extensao = extensoes.get(formato, '.jpg')

        caminho_saida = filedialog.asksaveasfilename(
            title=f"Salvar como {formato}",
            defaultextension=extensao,
            initialfile=f"{Path(self.caminho_imagem).stem}_comprimido{extensao}"
        )

        if not caminho_saida:
            return

        try:
            largura = int(self.var_largura.get()) if self.var_largura.get() else None
            altura = int(self.var_altura.get()) if self.var_altura.get() else None
            tamanho_max = float(self.var_tamanho.get()) if self.var_tamanho.get() else None
        except ValueError:
            messagebox.showerror("Erro", "Digite apenas números!")
            return

        config = {
            'width': largura, 'height': altura,
            'max_size_kb': tamanho_max if formato == 'JPEG' else None,
            'quality': self.var_qualidade.get(),
            'format': formato,
            'keep_ratio': self.var_proporcao.get()
        }

        self.btn_comprimir.configure(state="disabled", text="⏳ Processando...")
        self.barra_progresso.grid()
        self.barra_progresso.set(0)

        thread = CompressionThread(self.caminho_imagem, caminho_saida, config, self._callback_compressao)
        thread.start()

    def _callback_compressao(self, status, *args):
        self.after(0, self._processar_resultado, status, *args)

    def _processar_resultado(self, status, *args):
        if status == "progress":
            pct, msg = args
            self.barra_progresso.set(pct / 100)
            self.label_progresso.configure(text=msg)

        elif status == "finished":
            caminho, final_kb, qualidade, original_kb = args

            self.barra_progresso.set(1)
            self.barra_progresso.grid_remove()
            self.label_progresso.configure(text="")

            reducao = (1 - final_kb / original_kb) * 100 if original_kb > 0 else 0

            if reducao >= 0:
                resultado = (f"✅ Comprimido com sucesso!\n\n"
                             f"📄 Original: {original_kb:.1f} KB\n"
                             f"🗜️ Final: {final_kb:.1f} KB\n"
                             f"📊 Redução: {reducao:.1f}%")
            else:
                resultado = (f"⚠️ Arquivo aumentou\n\n"
                             f"📄 Original: {original_kb:.1f} KB\n"
                             f"🗜️ Final: {final_kb:.1f} KB\n"
                             f"📊 Aumento: {abs(reducao):.1f}%\n\n"
                             f"Tente outro formato ou reduza as dimensões")

            if qualidade > 0:
                resultado += f"\n✨ Qualidade: {qualidade}%"

            self.texto_resultado.configure(state="normal")
            self.texto_resultado.delete("1.0", "end")
            self.texto_resultado.insert("1.0", resultado)
            self.texto_resultado.configure(state="disabled")

            self.btn_comprimir.configure(state="normal", text="🚀 Comprimir Imagem")

            try:
                self.imagem_preview = Image.open(caminho)
                self._atualizar_preview()
            except:
                pass

            messagebox.showinfo("Sucesso", f"Compressão concluída!\nRedução de {reducao:.1f}%")

        elif status == "error":
            msg = args[0]
            self.barra_progresso.grid_remove()
            self.label_progresso.configure(text="")
            self.btn_comprimir.configure(state="normal", text="🚀 Comprimir Imagem")
            messagebox.showerror("Erro", f"Falha:\n{msg}")


def main():
    app = ImageCompressor()
    app.mainloop()


if __name__ == "__main__":
    main()