[🇧🇷] [Lê em português](README.pt.md)

# 🖼️ Compress Image - Python Image Optimizer (v1.1.0)

**A modular Python CLI tool for efficient image compression, resizing, and format conversion**  
Now with a clean architecture, type hints, and extensible components.

---

## 🚀 Key Improvements (v1.1.0+)
- **Refactored Core**:
  - OOP-based modular design (`compressor.py`, `converter.py`, `resizer.py`)
  - Type hints and dataclasses for better maintainability
  - Separation of concerns (CLI parsing vs. engine logic)
- **New Features**:
  - Support for both Windows (`.bat`) and Linux (`.sh`) one-click scripts
  - Configurable via `CompressionOptions` and `ResizeOptions` classes
- **Simplified Usage**:
  - Same CLI interface (backward compatible)
  - Better error handling and validation

---

## 📸 Comparison of Results

| Original (80.3KB) | Optimized (28.9KB) |
|------------------|-------------------|
| <img src="./assets/img.jpeg" width="300"> | <img src="./assets/reduced_image.jpeg" width="300"> |

*64% reduction in size while maintaining visual quality.*

---

## ⚙️ Updated Architecture
```bash
src/
├── core/               # Business logic
│   ├── compressor.py   # Size/quality optimization
│   ├── converter.py    # Format conversion (JPEG/PNG)
│   ├── resizer.py      # Smart resizing (thumbnail/force)
│   ├── models.py       # Dataclasses for options
│   └── engine.py       # Orchestration
└── imgpress/           # CLI layer
    ├── parser.py       # Argument parsing
    └── args_parser.py  # Parser interface
```

---

## 🧾 How to Use (Same Simple Interface)

### Basic Command:
```bash
python main.py input.jpg output.jpg [options]
```

### Popular Options:
| Option          | Description                          |
|-----------------|--------------------------------------|
| `--max-width`   | Maximum output width (pixels)        |
| `--max-height`  | Maximum output height (pixels)       |
| `--max-size-kb` | Target filesize (KB)                 |
| `--quality`     | JPEG quality (1-100)                 |
| `--jpeg`        | Force JPEG output                    |
| `--redim`       | Keep aspect ratio when resizing      |

---

## 🪟 One-Click Usage
**Windows** (`dim_img.bat`):
```bat
@echo off
python main.py img.jpg optimized.jpg --max-width 1280 --quality 85 --jpeg
```

**Linux/macOS** (`dim_img.sh`):
```bash
python3 main.py img.jpg optimized.jpg \
  --max-width 1280 \
  --quality 85 \
  --jpeg
```

---

## ✅ Why This Version Rocks
1. **Future-proof** - Easy to add new features (e.g., WebP support)
2. **Maintainable** - Clear separation of concerns
3. **Reliable** - Type hints reduce runtime errors
4. **Consistent** - Same simple CLI for end-users

---

> 💡 **Pro Tip**: Use `--redim` for social media images and `--max-size-kb` for email attachments!