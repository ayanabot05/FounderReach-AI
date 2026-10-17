import logging
import urllib.parse
import urllib.request
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from founderreach.config import settings
from founderreach.models import DiscussionItem, ProductProfile
from founderreach.connectors.base import BaseConnector
from founderreach.db import db

logger = logging.getLogger(__name__)

class HackerNewsConnector(BaseConnector):
    def __init__(self):
        super().__init__("Hacker News")
        self.api_base = settings.HN_API_BASE
        self.user_agent = "FounderReach-AI/1.0 (Public Research; Algolia API)"

    def is_enabled(self) -> bool:
        return settings.HN_ENABLED

    def _clean_html(self, raw_html: str) -> str:
        """Strips HTML entities and tags commonly returned by HN Algolia API."""
        if not raw_html:
            return ""
        # Replace <p> with newlines
        text = re.sub(r'<p>', '\n\n', raw_html)
        text = re.sub(r'<a\s+(?:[^>]*?\s+)?href="([^"]*)"[^>]*>(.*?)</a>', r'\2 (\1)', text)
        # Strip other HTML tags
        text = re.sub(r'<[^<]+?>', '', text)
        # Unescape HTML entities
        import html
        text = html.unescape(text)
        return text.strip()

    def _execute_query(self, query: str, tags: str = "comment", hits_per_page: int = 25) -> List[Dict[str, Any]]:
        """Queries the Algolia Hacker News Search API with caching."""
        cache_key = f"hn_search:{tags}:{query}:{hits_per_page}"
        cached = db.get_cache(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        params = {
            "query": query,
            "tags": tags,
            "hitsPerPage": hits_per_page
        }
        url = f"{self.api_base}/search?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    hits = payload.get("hits", [])
                    db.set_cache(cache_key, json.dumps(hits))
                    return hits
        except Exception as e:
            logger.error(f"Error querying Hacker News Algolia API for query '{query}': {e}")
            return []
        return []

    def search(self, product: ProductProfile, limit: int = 30) -> List[DiscussionItem]:
        if not self.is_enabled():
            logger.warning("Hacker News connector is disabled.")
            return []

        # Formulate targeted search queries from product profile
        targeted_queries = []
        if product.keywords:
            targeted_queries.extend(product.keywords)
        if product.pain_points:
            targeted_queries.extend(product.pain_points)
            
        # Add high-intent phrases specific to product domain
        targeted_queries.extend([
            "elderly parents living alone",
            "aging parents check in",
            "taking care of elderly parents",
            "parents live alone",
            "parents in India",
            "medicine reminder parents",
            "elder care whatsapp",
            "nri parents alone"
        ])
            
        # Deduplicate queries
        unique_queries = list(dict.fromkeys(targeted_queries))
        
        seen_ids = set()
        discussions: List[DiscussionItem] = []

        for q in unique_queries:
            if len(discussions) >= limit:
                break
                
            # Search comments (where real people express needs)
            hits = self._execute_query(q, tags="comment", hits_per_page=20)
            for hit in hits:
                item_id = str(hit.get("objectID"))
                if item_id in seen_ids:
                    continue
                seen_ids.add(item_id)

                raw_text = hit.get("comment_text") or ""
                clean_text = self._clean_html(raw_text)
                
                # Filter out very short or empty comments
                if len(clean_text) < 50:
                    continue

                created_at = None
                if hit.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(hit["created_at"].replace("Z", "+00:00"))
                    except Exception:
                        pass

                story_title = hit.get("story_title") or hit.get("title") or "Hacker News Discussion"
                original_url = f"https://news.ycombinator.com/item?id={item_id}"
                
                discussion = DiscussionItem(
                    id=f"hn_{item_id}",
                    platform="Hacker News",
                    original_url=original_url,
                    title=story_title,
                    author=hit.get("author"),
                    text=clean_text,
                    created_at=created_at,
                    raw_metadata={
                        "story_id": hit.get("story_id"),
                        "points": hit.get("points"),
                        "parent_id": hit.get("parent_id")
                    }
                )
                discussions.append(discussion)
                if len(discussions) >= limit:
                    break

        return discussions
