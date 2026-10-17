import logging
from typing import List
from founderreach.config import settings
from founderreach.models import DiscussionItem, ProductProfile
from founderreach.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class RedditConnector(BaseConnector):
    """
    Reddit API Connector.
    
    COMPLIANCE DIRECTIVE:
    Per CEO execution instructions, this integration MUST remain disabled
    until explicit commercial-use Reddit API authorization is granted.
    Scraping without API authorization or bypassing Reddit's terms is strictly forbidden.
    """
    def __init__(self):
        super().__init__("Reddit")
        self.enabled = settings.REDDIT_ENABLED

    def is_enabled(self) -> bool:
        return self.enabled

    def search(self, product: ProductProfile, limit: int = 25) -> List[DiscussionItem]:
        if not self.is_enabled():
            logger.info("Reddit connector is disabled by policy (awaiting commercial API authorization).")
            return []
            
        # If enabled in future after CEO approval & commercial OAuth setup:
        # Client ID, Client Secret, and OAuth tokens are strictly validated here.
        raise NotImplementedError("Reddit integration requires active commercial API authorization credentials.")
