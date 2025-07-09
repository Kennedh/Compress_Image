[🇬🇧] Read in English

# 🖼️ Compress Image - Otimizador de Imagens em Python (v1.1.0)

**Ferramenta CLI modular para compressão, redimensionamento e conversão de imagens**  
Agora com arquitetura limpa, type hints e componentes extensíveis.

---

## 🚀 Melhorias Principais (v1.1.0+)
- **Núcleo Refatorado**:
  - Design modular orientado a objetos (`compressor.py`, `converter.py`, `resizer.py`)
  - Type hints e dataclasses para melhor manutenção
  - Separação clara entre lógica de CLI e processamento
- **Novos Recursos**:
  - Scripts one-click para Windows (`.bat`) e Linux (`.sh`)
  - Configuração via classes `CompressionOptions` e `ResizeOptions`
- **Mesma Simplicidade**:
  - Interface CLI idêntica (compatível com versões anteriores)
  - Tratamento de erros aprimorado

---

## 📸 Comparação de Resultados

| Original (80.3KB) | Otimizada (28.9KB) |
|------------------|-------------------|
| <img src="./assets/img.jpeg" width="300"> | <img src="./assets/reduced_image.jpeg" width="300"> |

*Redução de 64% no tamanho mantendo qualidade visual*

---

## ⚙️ Arquitetura Atualizada
```bash
src/
├── core/               # Lógica principal
│   ├── compressor.py   # Otimização por tamanho/qualidade
│   ├── converter.py    # Conversão entre formatos (JPEG/PNG)
│   ├── resizer.py      # Redimensionamento inteligente
│   ├── models.py       # Opções configuráveis
│   └── engine.py       # Orquestração
└── imgpress/           # Interface CLI
    ├── parser.py       # Parsing de argumentos
    └── args_parser.py  # Interface de parsing
```

---

## 🧾 Como Usar (Mesma Interface Simples)

### Comando Básico:
```bash
python main.py entrada.jpg saida.jpg [opções]
```

### Opções Populares:
| Opção          | Descrição                          |
|----------------|------------------------------------|
| `--max-width`  | Largura máxima (pixels)            |
| `--max-height` | Altura máxima (pixels)             |
| `--max-size-kb`| Tamanho máximo alvo (KB)           |
| `--quality`    | Qualidade JPEG (1-100)             |
| `--jpeg`       | Forçar saída em JPEG               |
| `--redim`      | Manter proporção ao redimensionar  |

---

## 🪟 Uso com Um Clique
**Windows** (`scripts/dim_img.bat`):
```bat
@echo off
python main.py img.jpg otimizada.jpg --max-width 1280 --quality 85 --jpeg
```

**Linux/macOS** (`scripts/dim_img.sh`):
```bash
python3 main.py img.jpg otimizada.jpg \
  --max-width 1280 \
  --quality 85 \
  --jpeg
```

---

## ✅ Vantagens desta Versão
1. **Pronta para o futuro** - Fácil adição de novos formatos (ex: WebP)
2. **Manutenção fácil** - Código organizado e documentado
3. **Confiança** - Type hints reduzem erros
4. **Consistência** - Mesma CLI simples para usuários finais

---

> 💡 **Dica**: Use `--redim` para redes sociais e `--max-size-kb` para anexos de e-mail!