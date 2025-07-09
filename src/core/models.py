from dataclasses import dataclass
from typing import Optional

@dataclass
class ResizeOptions:
    max_width: Optional[int]
    max_height: Optional[int]
    keep_aspect_ratio: bool = True

@dataclass
class CompressionOptions:
    format: str  # 'jpeg' ou 'png'
    max_size_kb: Optional[int]
    quality: Optional[int] = 85
