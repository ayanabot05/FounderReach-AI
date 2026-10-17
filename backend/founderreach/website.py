"""Bounded fetch of a founder-supplied public HTML page.

DNS is checked and the connection is pinned to the checked IP for every hop.
No scripts, images, CSS or secondary URLs are fetched.
"""
import http.client
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit, urlunsplit


class WebsiteFetchError(ValueError):
    pass


class UnsafeWebsiteError(WebsiteFetchError):
    pass


class _VisibleHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.keywords = ""
        self.headings = []
        self.body = []
        self._tag = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style", "noscript"):
            self._skip += 1
        if tag in ("title", "h1", "h2"):
            self._tag = tag
        if tag == "meta":
            name = (attrs.get("name") or attrs.get("property") or "").lower()
            if name in ("description", "og:description") and not self.description:
                self.description = (attrs.get("content") or "").strip()[:500]
            if name == "keywords":
                self.keywords = (attrs.get("content") or "").strip()[:300]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
        if tag == self._tag:
            self._tag = None

    def handle_data(self, data):
        if self._skip:
            return
        value = " ".join(data.split())
        if not value:
            return
        if self._tag == "title":
            self.title += value + " "
        elif self._tag in ("h1", "h2") and len(self.headings) < 8:
            self.headings.append(value[:160])
        elif len(self.body) < 100:
            self.body.append(value[:300])


class WebsiteFetcher:
    max_bytes = 512_000
    max_redirects = 3
    timeout_seconds = 5

    def _target(self, url):
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            raise UnsafeWebsiteError("Enter a public HTTP or HTTPS website URL")
        if parsed.username or parsed.password or parsed.fragment:
            raise UnsafeWebsiteError("URL credentials and fragments are not accepted")
        try:
            port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
        except ValueError as exc:
            raise UnsafeWebsiteError("Invalid port") from exc
        if port != (443 if parsed.scheme.lower() == "https" else 80):
            raise UnsafeWebsiteError("Only the standard port for this URL scheme is allowed")
        host = parsed.hostname.encode("idna").decode("ascii").rstrip(".").lower()
        if not host or "." not in host or len(host) > 253:
            raise UnsafeWebsiteError("A public domain name is required")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise UnsafeWebsiteError("IP-address URLs are not allowed")
        if host.endswith((".local", ".internal", ".localhost", ".test", ".invalid")):
            raise UnsafeWebsiteError("Private or reserved domains are not allowed")
        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except OSError as exc:
            raise WebsiteFetchError("Website domain could not be resolved") from exc
        ips = [record[4][0] for record in addresses]
        if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
            raise UnsafeWebsiteError("Website resolves to a private or unsafe network")
        path = parsed.path or "/"
        if len(url) > 2048:
            raise UnsafeWebsiteError("Website URL is too long")
        clean = urlunsplit((parsed.scheme.lower(), host + (f":{port}" if port not in (80, 443) else ""), path, parsed.query, ""))
        return clean, host, port, ips[0], path + (f"?{parsed.query}" if parsed.query else "")

    def _request(self, scheme, host, port, ip, path):
        connector = http.client.HTTPSConnection if scheme == "https" else http.client.HTTPConnection
        conn = connector(host, port=port, timeout=self.timeout_seconds)
        conn._create_connection = lambda address, timeout=None, source_address=None: socket.create_connection(
            (ip, port), timeout=self.timeout_seconds, source_address=source_address)
        try:
            conn.request("GET", path, headers={"Host": host, "User-Agent": "FounderReach/1.0 (single-page founder-requested research)",
                                                "Accept": "text/html", "Accept-Encoding": "identity"})
            response = conn.getresponse()
            body = response.read(self.max_bytes + 1)
            return response.status, dict((k.lower(), v) for k, v in response.getheaders()), body
        except (OSError, http.client.HTTPException) as exc:
            raise WebsiteFetchError("Website could not be reached within the time limit") from exc
        finally:
            conn.close()

    def fetch(self, url):
        current = url
        for hop in range(self.max_redirects + 1):
            clean, host, port, ip, path = self._target(current)
            status, headers, body = self._request(urlsplit(clean).scheme, host, port, ip, path)
            if status in (301, 302, 303, 307, 308):
                if hop >= self.max_redirects:
                    raise WebsiteFetchError("Website redirected too many times")
                location = headers.get("location")
                if not location:
                    raise WebsiteFetchError("Website returned a redirect without a destination")
                current = urljoin(clean, location)
                continue
            if status != 200:
                raise WebsiteFetchError(f"Website returned HTTP {status}")
            if len(body) > self.max_bytes:
                raise WebsiteFetchError("Website page exceeded the size limit")
            if "text/html" not in headers.get("content-type", "").lower():
                raise WebsiteFetchError("Website did not return an HTML page")
            if headers.get("content-encoding", "identity").lower() != "identity":
                raise WebsiteFetchError("Compressed responses are not supported")
            parser = _VisibleHTML()
            parser.feed(body.decode("utf-8", errors="replace"))
            return {"url": clean, "title": parser.title.strip()[:200],
                    "description": parser.description, "keywords": parser.keywords,
                    "headings": parser.headings[:8], "text_excerpt": " ".join(parser.body)[:1200]}
        raise WebsiteFetchError("Website could not be fetched")


def propose_profile(snapshot):
    title = snapshot.get("title", "").split("|")[0].split("—")[0].strip()
    name = title[:80] or urlsplit(snapshot["url"]).hostname or "New business"
    description = snapshot.get("description") or ""
    keywords = [part.strip() for part in snapshot.get("keywords", "").split(",") if part.strip()][:12]
    return {"name": name, "website": snapshot["url"], "description": description,
            "target_audiences": [], "pain_points": [], "keywords": keywords,
            "negative_keywords": [], "customer_fit_signals": [], "supported_languages": [],
            "target_markets": [], "acquisition_objectives": [], "competitor_names": [],
            "allowed_acquisition_channels": ["demand_evidence", "owned_channel"],
            "evidence": {"title": snapshot.get("title"), "description": description,
                         "headings": snapshot.get("headings", [])},
            "missing_information": [field for field in ("target_audiences", "pain_points", "competitor_names")],
            "confirmed": False}
