import urllib.request
import urllib.parse
import html
import re
import logging
from datetime import datetime, timedelta, timezone
from founderreach.models import SourceVerification

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
        parsed = urllib.parse.urlparse(url)
        host = parsed.hostname
        if parsed.scheme != "https" or host != "news.ycombinator.com" or parsed.path != "/item" or not excerpt.strip():
            return SourceVerification(verified=False, http_status=None, verified_url=url,
                evidence_excerpt=excerpt, verification_notes="Unsupported source or empty excerpt",
                status="unsupported_source")

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
                final_url = resp.geturl() if hasattr(resp, "geturl") else url
                if isinstance(final_url, str) and (urllib.parse.urlparse(final_url).hostname != host
                                                   or urllib.parse.urlparse(final_url).scheme != "https"):
                    return SourceVerification(verified=False, http_status=status_code, verified_url=url,
                        evidence_excerpt=excerpt, verification_notes="Redirected outside approved source",
                        status="unsupported_source")
                if status_code != 200:
                    res = SourceVerification(
                        verified=False,
                        http_status=status_code,
                        verified_url=url,
                        evidence_excerpt=excerpt,
                        verification_notes=f"HTTP status {status_code} is not 200 OK",
                        status="rate_limited" if status_code == 429 else "not_found" if status_code == 404 else "unverified"
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
                        verification_notes="Live URL reached and excerpt verified in page content.",
                        status="verified", method="hn_exact_quote",
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
                    )
                else:
                    res = SourceVerification(verified=False, http_status=status_code,
                        verified_url=url, evidence_excerpt=excerpt,
                        verification_notes="Live URL reached, but full quoted excerpt was absent.",
                        status="quote_mismatch", method="hn_exact_quote")

                return res

        except urllib.error.HTTPError as e:
            return SourceVerification(verified=False, http_status=e.code, verified_url=url,
                evidence_excerpt=excerpt, status="rate_limited" if e.code == 429 else "not_found" if e.code == 404 else "unverified",
                method="hn_exact_quote", verification_notes=f"HTTP {e.code}")
        except Exception as e:
            logger.warning(f"Verification failed for {url}: {e}")
            res = SourceVerification(
                verified=False,
                http_status=None,
                verified_url=url,
                evidence_excerpt=excerpt,
                verification_notes=f"Network error during verification: {type(e).__name__}",
                status="network_error", method="hn_exact_quote"
            )
            return res

source_verifier = SourceVerifier()
