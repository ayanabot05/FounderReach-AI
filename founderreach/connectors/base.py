from abc import ABC, abstractmethod
from typing import List
from founderreach.models import DiscussionItem, ProductProfile

class BaseConnector(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(self, product: ProductProfile, limit: int = 25) -> List[DiscussionItem]:
        """Search the platform for customer discussions matching the product profile."""
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if connector is enabled and permitted to run."""
        pass
