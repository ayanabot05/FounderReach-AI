import hashlib
import re
import urllib.parse
from typing import Set, List
from founderreach.db import db

class Deduplicator:
    def __init__(self, jaccard_threshold: float = 0.80):
        self.jaccard_threshold = jaccard_threshold
        self._seen_urls: Set[str] = set()

    def canonicalize_url(self, url: str) -> str:
        """Strips query parameters like utm_*, ref, tracking tags, and fragments."""
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        # Keep only essential query parameters (e.g. id=... on news.ycombinator.com)
        query_dict = urllib.parse.parse_qs(parsed.query)
        cleaned_params = {}
        for k, v in query_dict.items():
            if not k.startswith("utm_") and k not in ("ref", "fbclid", "gclid"):
                cleaned_params[k] = v[0] if len(v) == 1 else v
        
        new_query = urllib.parse.urlencode(cleaned_params, doseq=True)
        canonical = urllib.parse.urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/'),
            "",
            new_query,
            ""
        ))
        return canonical

    def get_content_hash(self, text: str) -> str:
        """Computes a SHA-256 hash of normalized text."""
        norm_text = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(norm_text.encode('utf-8')).hexdigest()

    def _tokenize(self, text: str) -> Set[str]:
        return set(re.findall(r'\b[a-zA-Z]{3,}\b', text.lower()))

    def is_duplicate(self, url: str, text: str, existing_texts: List[str] = None) -> bool:
        """
        Returns True if:
        1. Canonical URL was already seen.
        2. Exact content hash is found in database or current run.
        3. Near-duplicate similarity exceeds jaccard_threshold against any existing text.
        """
        canon_url = self.canonicalize_url(url)
        if canon_url in self._seen_urls:
            return True

        content_hash = self.get_content_hash(text)
        if db.is_hash_seen(content_hash):
            return True

        # Check near-duplicates with existing texts
        if existing_texts:
            tokens_new = self._tokenize(text)
            if not tokens_new:
                return True
            for exist_text in existing_texts:
                tokens_exist = self._tokenize(exist_text)
                if not tokens_exist:
                    continue
                intersection = tokens_new.intersection(tokens_exist)
                union = tokens_new.union(tokens_exist)
                jaccard = len(intersection) / len(union) if union else 0.0
                if jaccard >= self.jaccard_threshold:
                    return True

        # Mark as seen in this session
        self._seen_urls.add(canon_url)
        return False

    def mark_saved(self, opp_id: str, url: str, text: str):
        content_hash = self.get_content_hash(text)
        db.record_content_hash(content_hash, opp_id, self.canonicalize_url(url))

deduplicator = Deduplicator()
