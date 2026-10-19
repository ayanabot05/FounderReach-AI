"""Reddit API Connector for FounderReach AI

Complies with Reddit API Data Policy and commercial OAuth usage:
- OAuth2 Client Credentials flow for programmatic retrieval
- Reads public discussions from targeted software & founder subreddits
- Defaults to disabled unless explicit API credentials are provided in settings/environment
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
import json
import logging
from typing import List, Optional
import urllib.parse
import urllib.request

from founderreach.config import settings
from founderreach.connectors.base import BaseConnector
from founderreach.models import DiscussionItem, ProductProfile

logger = logging.getLogger(__name__)


class RedditConnector(BaseConnector):
    """Reddit OAuth API Connector for founder discussion discovery."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        enabled: Optional[bool] = None,
    ):
        super().__init__("Reddit")
        self.client_id = client_id or settings.REDDIT_CLIENT_ID
        self.client_secret = client_secret or settings.REDDIT_CLIENT_SECRET
        self.user_agent = user_agent or settings.REDDIT_USER_AGENT
        # By default, disabled unless explicit commercial credentials are provided or enabled flag is True
        self._enabled = (
            enabled
            if enabled is not None
            else (bool(self.client_id and self.client_secret) and settings.REDDIT_ENABLED)
        )
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0

    def is_enabled(self) -> bool:
        """Connector is enabled only when credentials and approval are present."""
        return bool(self._enabled and self.client_id and self.client_secret)

    def _get_access_token(self) -> Optional[str]:
        """Obtain an OAuth2 Bearer token from Reddit API using client_credentials."""
        if not self.client_id or not self.client_secret:
            return None

        # Return cached token if still valid
        now = datetime.now(timezone.utc).timestamp()
        if self._access_token and now < self._token_expires_at - 60:
            return self._access_token

        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode("utf-8")).decode("utf-8")
        data = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode("utf-8")

        req = urllib.request.Request(
            "https://www.reddit.com/api/v1/access_token",
            data=data,
            headers={
                "Authorization": f"Basic {auth_header}",
                "User-Agent": self.user_agent,
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    self._access_token = payload.get("access_token")
                    expires_in = payload.get("expires_in", 3600)
                    self._token_expires_at = now + expires_in
                    return self._access_token
        except Exception as exc:
            logger.error(f"Failed to acquire Reddit OAuth token: {exc}")
            return None

    def search(self, product: ProductProfile, limit: int = 25) -> List[DiscussionItem]:
        """Search public subreddit discussions relevant to the product profile."""
        if not self.is_enabled():
            logger.info("Reddit connector is disabled by policy (awaiting commercial API authorization).")
            return []

        token = self._get_access_token()
        if not token:
            logger.warning("Reddit API credentials invalid or token request failed.")
            return []

        keywords = product.keywords or [product.name]
        query = " OR ".join(f'"{kw}"' for kw in keywords[:3])
        subreddits = "SaaS+SideProject+Entrepreneur+webdev"
        params = urllib.parse.urlencode({
            "q": query,
            "sort": "new",
            "limit": min(limit, 50),
            "restrict_sr": 1
        })

        url = f"https://oauth.reddit.com/r/{subreddits}/search.json?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "User-Agent": self.user_agent
            }
        )

        items: List[DiscussionItem] = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    children = data.get("data", {}).get("children", [])
                    for post in children:
                        pdata = post.get("data", {})
                        post_id = pdata.get("id")
                        title = pdata.get("title", "")
                        selftext = pdata.get("selftext", "")
                        permalink = pdata.get("permalink", "")
                        author = pdata.get("author", "[deleted]")
                        created_utc = pdata.get("created_utc")

                        if not post_id or not permalink:
                            continue

                        full_url = f"https://www.reddit.com{permalink}"
                        created_dt = (
                            datetime.fromtimestamp(created_utc, timezone.utc)
                            if created_utc
                            else datetime.now(timezone.utc)
                        )

                        items.append(
                            DiscussionItem(
                                id=f"reddit_{post_id}",
                                platform="Reddit",
                                original_url=full_url,
                                title=title,
                                author=author,
                                text=selftext or title,
                                created_at=created_dt,
                                raw_metadata={
                                    "subreddit": pdata.get("subreddit"),
                                    "score": pdata.get("score"),
                                    "num_comments": pdata.get("num_comments")
                                }
                            )
                        )
        except Exception as exc:
            logger.error(f"Reddit search request failed: {exc}")

        return items


def fetch_live_reddit_discussions(query: str, limit: int = 10) -> List[dict]:
    """Helper to fetch live Reddit discussions if connector is enabled, else returns safe status."""
    connector = RedditConnector()
    if not connector.is_enabled():
        return [{
            "status": "DISABLED_BY_POLICY",
            "message": "Reddit OAuth API is ready. Set REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_ENABLED=true in .env to activate live streaming.",
            "source": "Reddit",
            "query": query
        }]

    # When enabled, execute search with temporary mock profile
    from founderreach.models import ProductProfile
    temp_profile = ProductProfile(
        name=query,
        description=f"Search target: {query}",
        keywords=[query]
    )
    items = connector.search(temp_profile, limit=limit)
    return [item.model_dump() for item in items]
