from .core import CompressionEngine, ResizeOptions, CompressionOptions
from .imgpress import args

fmt = 'jpeg' if args.jpeg else 'png'

resize_opts = ResizeOptions(
    max_height=args.max_height, 
    max_width=args.max_width, 
    keep_aspect_ratio=args.redim
)

comp_opts = CompressionOptions(
    format=fmt, 
    max_size_kb=args.max_size_kb,
    quality=args.quality
)

engine = CompressionEngine(
    input_path=args.input,
    output_path=args.output,
    resize_opts=resize_opts,
    comp_opts=comp_opts
)

__all__ = ["engine"]

__author__ = "Eric Santos <ericshantos13@gmail.com" 
