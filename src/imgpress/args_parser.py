from abc import ABC, abstractmethod
from typing import List, Optional

class ArgsParser(ABC):
    @abstractmethod
    def parse(self, argv: List[Optional[str]] = None):
        pass