
# 🖼️ Compress Image - Redutor e Otimizador de Imagens em Python

Este script Python realiza **compressão, redimensionamento e conversão de imagens** de forma prática e eficiente, com suporte a JPEG e PNG.

Ideal para:
- Otimizar imagens para web, WhatsApp, apresentações, etc.
- Converter imagens para JPEG reduzindo o tamanho
- Redimensionar mantendo ou não a proporção

---

## ⚙️ Tecnologias e Bibliotecas

- [Python 3.x](https://www.python.org/)
- [Pillow (PIL)](https://pillow.readthedocs.io/en/stable/)

Instale com:
```bash
pip install pillow
```

---

## 🧾 Como usar

### Comando básico:
```bash
python compress_image.py <entrada> <saida> [opções]
```

---

## 📥 Argumentos disponíveis

| Argumento             | Tipo     | Descrição                                                                 |
|-----------------------|----------|---------------------------------------------------------------------------|
| `input`               | obrigatório | Caminho da imagem de entrada                                              |
| `output`              | obrigatório | Caminho da imagem de saída                                                |
| `--max-width`         | inteiro  | Largura máxima da imagem (em pixels)                                      |
| `--max-height`        | inteiro  | Altura máxima da imagem (em pixels)                                       |
| `--max-size-kb`       | float    | Tamanho máximo em KB (apenas para JPEG)                                   |
| `--quality`           | inteiro  | Qualidade do JPEG (padrão: 70)                                            |
| `--jpeg`              | flag     | Converte a imagem para formato JPEG                                       |
| `--redim`             | flag     | Mantém a proporção ao redimensionar (`True` = thumbnail, `False` = resize forçado) |

---

## 💡 Exemplos práticos

### 🔹 Reduzir mantendo proporção para caber em uma apresentação
```bash
python compress_image.py imagem.jpg imagem_720p.jpg --max-width 1280 --max-height 720 --jpeg --redim
```

### 🔹 Comprimir imagem JPEG até 300KB
```bash
python compress_image.py selfie.png selfie_compacta.jpg --max-size-kb 300 --jpeg
```

### 🔹 Redimensionar para 800x800 sem manter proporção
```bash
python compress_image.py produto.png produto_800x800.jpg --max-width 800 --max-height 800 --jpeg
```

### 🔹 Converter PNG para PNG indexado (64 cores)
```bash
python compress_image.py banner.png banner_otimizado.png
```

---

## 🪟 Uso no Windows via `.bat`

Crie um arquivo chamado `reduzir.bat` com o seguinte conteúdo:

```bat
@echo off
python compress_image.py img.jpg reduzida.jpg --max-width 1000 --max-height 1000 --max-size-kb 400 --quality 80 --jpeg --redim
pause
```

Depois basta arrastar a imagem para a pasta e rodar o `.bat`.

---



## ✅ Resultado esperado

- Imagens otimizadas com qualidade visual preservada
- Arquivos menores para envio ou publicação
- Ajuste fácil de tamanho e proporção

---

## ✨ Autor

Desenvolvido por [Seu Nome] — Compartilhe, use e melhore como quiser!
