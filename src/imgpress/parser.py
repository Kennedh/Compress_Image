from argparse import ArgumentParser, Namespace
from .args_parser import ArgsParser
from typing import Optional, List

class Parser(ArgsParser):
    def __init__(self) -> None:
        self._parse = ArgumentParser(description="Compress and resize images efficiently!")
        self._configure()

    def _configure(self) -> None:
        self._parse.add_argument("input", help="Input image path")
        self._parse.add_argument("output", help="Output image path")
        self._parse.add_argument("--max-width", type=int, help="Width maximum")
        self._parse.add_argument("--max-height", type=int, help="Height maximum")
        self._parse.add_argument("--max-size-kb", type=float, help="Length maximum in KB (only KPEG!)")
        self._parse.add_argument("--quality", type=int, default=70, help="JPEG quality (standard 70)")
        self._parse.add_argument("--jpeg", action="store_true", help="Save to JPEG")
        self._parse.add_argument("--redim", action="store_true", help="Resize the image respecting the aspect ratio")

    def parse(self, argv: Optional[List[str]] = None) -> Namespace:
        return self._parse.parse_args(argv)
    