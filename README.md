# 🖼️ Compress Image Pro - Redutor e Otimizador de Imagens

Um aplicativo desktop completo desenvolvido em Python para realizar **compressão, redimensionamento e conversão de imagens** de forma inteligente e visual. 

A ferramenta analisa a imagem e aplica as melhores técnicas de compressão preservando a qualidade visual, agora com uma interface gráfica moderna e suporte a novos formatos.

---

## ✨ Novidades da Versão Pro

- 🖥️ **Interface Gráfica (GUI):** Adeus linha de comando! Interface moderna construída com `customtkinter`.
- 👁️ **Preview em Tempo Real:** Visualize as mudanças de proporção e tamanho antes de salvar.
- 🧠 **Compressão Inteligente:** 
  - Otimização fotográfica automática (ajuste fino de nitidez e contraste).
  - Preservação inteligente de transparência (Alpha channel).
  - Análise de paleta de cores para não inflar arquivos PNG ou WEBP atoa.
- 🚀 **Multithreading:** A interface não trava enquanto imagens pesadas são processadas.
- 🔄 **Novos Formatos:** Suporte completo a **WEBP** (Lossy e Lossless), além de JPEG e PNG.

---

## ⚙️ Tecnologias e Bibliotecas

- [Python 3.x](https://www.python.org/)
- [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/) - Processamento de imagens
- [CustomTkinter](https://customtkinter.tomschimansky.com/) - Interface gráfica moderna

### Instalação

Clone o repositório e instale as dependências via `pip`:

```bash
pip install pillow customtkinter
```

## 📥 Formatos Suportados

### 🔽 Entrada

| ✅ | Formato | Extensões |
|---|---------|-----------|
| ✅ | JPEG | `.jpg`, `.jpeg` |
| ✅ | PNG | `.png` |
| ✅ | BMP | `.bmp` |
| ✅ | GIF | `.gif` |
| ✅ | TIFF | `.tiff`, `.tif` |
| ✅ | WEBP | `.webp` |
| ✅ | ICO | `.ico` |
| ✅ | Outros | `.ppm`, `.pgm`, `.pcx`, `.tga` |

### 🔼 Saída

| ✅ | Formato | Extensão | Ideal para |
|---|---------|----------|------------|
| ✅ | JPEG | `.jpg` | Fotos e imagens sem transparência |
| ✅ | PNG | `.png` | Imagens com transparência ou gráficos |
| ✅ | WEBP | `.webp` | Web moderna, melhor compressão |

---

## 📊 Comparativo de Versões

| Funcionalidade | Versão Terminal (v1.0) | Versão GUI (v2.0) ✨ |
|:---|:---:|:---:|
| **Interface** | `Linha de comando` | `Interface gráfica moderna` |
| **Preview** | ❌ | ✅ Tempo real |
| **Formatos de saída** | JPEG, PNG | JPEG, PNG, **WEBP** 🆕 |
| **Compressão inteligente** | Básica | **Avançada** (nunca aumenta) |
| **Otimização de fotos** | ❌ | ✅ Nitidez + contraste automático |
| **Transparência** | ⚠️ Perdida ao converter | ✅ Preservada e tratada |
| **Tema** | N/A | 🌓 Claro/Escuro automático |
| **Progresso** | Terminal | 📊 Barra de progresso visual |
| **Arrastar e soltar** | ❌ | ❌ *(planejado)* |
| **Processamento em lote** | ❌ | ❌ *(planejado)* |
