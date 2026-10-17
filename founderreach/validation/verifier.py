import urllib.request
import urllib.parse
import html
import re
import hashlib
import logging
from datetime import datetime
from typing import Tuple, Optional
from founderreach.models import SourceVerification
from founderreach.db import db

logger = logging.getLogger(__name__)

class SourceVerifier:
    def __init__(self, timeout: int = 8):
        self.timeout = timeout
        self.user_agent = "FounderReach-Verification/1.0 (+https://github.com/founderreach/verification-bot)"

    def _normalize_text(self, text: str) -> str:
        """Normalizes text for substring verification across whitespace and HTML encoding."""
        if not text:
            return ""
        text = html.unescape(text)
        # Remove markdown/html markup
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'[\r\n\t]+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()

    def verify_source(self, url: str, excerpt: str) -> SourceVerification:
        """
        Performs live HTTP verification:
        1. Checks HTTP status (must be 200 OK).
        2. Verifies that the excerpt actually exists in the live source HTML/body.
        3. Returns SourceVerification audit model.
        """
        # Check verification cache first
        host = urllib.parse.urlparse(url).hostname
        if host != "news.ycombinator.com" or not excerpt.strip():
            return SourceVerification(verified=False, http_status=None, verified_url=url,
                evidence_excerpt=excerpt, verification_notes="Unsupported source or empty excerpt")
        cache_key = f"verify:v2:{url}:{hashlib.sha256(excerpt.encode()).hexdigest()}"
        cached = db.get_cache(cache_key)
        if cached:
            try:
                import json
                data = json.loads(cached)
                data["checked_at"] = datetime.fromisoformat(data["checked_at"])
                return SourceVerification(**data)
            except Exception:
                pass

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                if status_code != 200:
                    res = SourceVerification(
                        verified=False,
                        http_status=status_code,
                        verified_url=url,
                        evidence_excerpt=excerpt,
                        verification_notes=f"HTTP status {status_code} is not 200 OK"
                    )
                    return res

                # Read body content
                raw_bytes = resp.read(500000)  # Read up to 500KB
                body = raw_bytes.decode('utf-8', errors='ignore')
                
                norm_body = self._normalize_text(body)
                norm_excerpt = self._normalize_text(excerpt)
                
                # Require the entire normalized quote. Shared keywords are not source proof.
                if len(norm_excerpt) >= 30 and norm_excerpt in norm_body:
                    res = SourceVerification(
                        verified=True,
                        http_status=status_code,
                        verified_url=url,
                        evidence_excerpt=excerpt[:250],
                        verification_notes="Live URL reached and excerpt verified in page content."
                    )
                else:
                    res = SourceVerification(verified=False, http_status=status_code,
                        verified_url=url, evidence_excerpt=excerpt,
                        verification_notes="Live URL reached, but full quoted excerpt was absent.")

                # Cache result
                db.set_cache(cache_key, res.model_dump_json())
                return res

        except Exception as e:
            logger.warning(f"Verification failed for {url}: {e}")
            res = SourceVerification(
                verified=False,
                http_status=None,
                verified_url=url,
                evidence_excerpt=excerpt,
                verification_notes=f"Network error during verification: {str(e)}"
            )
            return res

source_verifier = SourceVerifier()
