"""Contratos independentes da interface, compatíveis com o Compress PDF."""

from dataclasses import dataclass
from pathlib import Path


class CompressionError(Exception):
    """Falha que pode ser apresentada ao usuário."""


class CompressionCancelled(CompressionError):
    """Cancelamento solicitado pelo usuário."""


@dataclass(frozen=True)
class CompressionResult:
    input_path: Path
    output_path: Path
    original_size: int
    compressed_size: int
    elapsed_seconds: float

    @property
    def saved_bytes(self):
        return self.original_size - self.compressed_size

    @property
    def reduction_percent(self):
        return 100 * self.saved_bytes / self.original_size if self.original_size else 0


def format_size(size):
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024 or unit == "TB":
            return f"{value:.1f} {unit}".replace(".", ",")
        value /= 1024


def next_output_path(source, folder, extension, reserved=()):
    """Sugere um nome livre; a publicação também verifica colisões."""
    source, folder = Path(source), Path(folder)
    target = folder / f"{source.stem}_comprimido{extension}"
    number = 2
    while target.exists() or target in reserved:
        target = folder / f"{source.stem}_comprimido_{number}{extension}"
        number += 1
    return target
