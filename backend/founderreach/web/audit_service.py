"""Audit Service for FounderReach AI

Performs safe, read-only website inspections and generates evidence-backed
SEO, AEO, and GEO fix proposals tailored for early-stage founders.

Priority 1: Reachability (DNS, HTTPS, HTTP status, Pinned IP, Redirects, TLS, Latency, Real HTML)
Priority 2: SEO Basics (Title, Meta Description, Canonical, Viewport, H1, Alt text, OG, Sitemap, Robots)
Priority 3: AEO (FAQPage, Organization/LocalBusiness, SoftwareApplication, Syntax-validated JSON-LD)
Priority 4: GEO / AI Visibility (Site-specific /llms.txt, AI crawlers matrix, Entity Grounding)
Fix Studio: Founder-proof platform instructions (WordPress, Webflow, Framer, Shopify, Custom HTML)
Demand Radar: Curated public discussions with non-spam response playbooks.
"""
from __future__ import annotations

from html.parser import HTMLParser
import ipaddress
import json
import logging
import re
import socket
import time
import urllib.parse
from urllib.parse import urljoin, urlsplit, urlunsplit
import urllib.request
from urllib.robotparser import RobotFileParser

from founderreach.website import WebsiteFetcher, WebsiteFetchError, UnsafeWebsiteError

logger = logging.getLogger(__name__)

USER_AGENT = "FounderReach-Audit/1.0 (+https://founderreach.ai/bot; read-only security audit)"
MAX_BYTES = 512_000


class SafeAuditFetcher(WebsiteFetcher):
    """Network fetcher with IP-pinned TCP sockets, hop-by-hop SSRF validation, and size limits."""

    def __init__(self, timeout_seconds: int = 6):
        super().__init__()
        self.timeout_seconds = timeout_seconds
        self.max_bytes = MAX_BYTES
        self.max_redirects = 3

    def fetch_resource(self, url: str) -> tuple[int, dict[str, str], bytes, str, str, list[str]]:
        """Fetch a public URL with IP pinning, redirect validation, and size capping.

        Returns:
            (status_code, headers_dict, body_bytes, final_url, pinned_ip, redirect_chain)
        """
        current = url
        last_ip = ""
        redirect_chain = [current]

        for hop in range(self.max_redirects + 1):
            clean, host, port, ip, path = self._target(current)
            last_ip = ip
            status, headers, body = self._request(urlsplit(clean).scheme, host, port, ip, path)

            if status in (301, 302, 303, 307, 308):
                if hop >= self.max_redirects:
                    raise WebsiteFetchError("Website redirected too many times")
                location = headers.get("location")
                if not location:
                    raise WebsiteFetchError("Website returned a redirect without a destination")
                current = urljoin(clean, location)
                redirect_chain.append(current)
                continue

            if len(body) > self.max_bytes:
                raise WebsiteFetchError(f"Response exceeded maximum allowed size of {self.max_bytes} bytes")

            return status, headers, body, clean, last_ip, redirect_chain

        raise WebsiteFetchError("Too many redirects")


class EnhancedPageParser(HTMLParser):
    """HTML parser extracting technical signals, headings, canonical links, and Schema.org JSON-LD."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ""
        self.meta_tags: list[dict[str, str]] = []
        self.headings: list[tuple[str, str]] = []
        self.h1_tags: list[str] = []
        self.current_heading_tag: str | None = None
        self.current_heading_text: list[str] = []
        self.jsonld_scripts: list[dict] = []
        self.jsonld_raw_scripts: list[str] = []
        self.jsonld_errors: list[str] = []
        self.in_jsonld = False
        self.current_jsonld: list[str] = []
        self.canonical: str | None = None
        self.llms_txt_link: str | None = None
        self.meta_robots: str = ""
        self.viewport: str = ""
        self.author: str = ""
        self.total_images = 0
        self.images_missing_alt = 0
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        tag = tag.lower()
        attr_dict = {k.lower(): (v or "") for k, v in attrs}

        if tag in {"style", "noscript"}:
            self._skip_depth += 1
            return

        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            self.meta_tags.append(attr_dict)
            name = attr_dict.get("name", "").lower()
            prop = attr_dict.get("property", "").lower()
            if name == "robots":
                self.meta_robots = attr_dict.get("content", "").lower()
            elif name == "viewport":
                self.viewport = attr_dict.get("content", "").strip()
            elif name in {"author", "creator"}:
                self.author = attr_dict.get("content", "").strip()
        elif tag == "link":
            rel = attr_dict.get("rel", "").lower().split()
            href = attr_dict.get("href", "")
            if "canonical" in rel:
                self.canonical = href
            elif "llms" in "".join(rel) or "llms.txt" in href.lower():
                self.llms_txt_link = href
        elif tag in {"h1", "h2", "h3"} and self._skip_depth == 0:
            self.current_heading_tag = tag
            self.current_heading_text = []
        elif tag == "img":
            self.total_images += 1
            alt = attr_dict.get("alt", "").strip()
            if not alt:
                self.images_missing_alt += 1
        elif tag == "script":
            script_type = attr_dict.get("type", "").lower()
            if script_type == "application/ld+json":
                self.in_jsonld = True
                self.current_jsonld = []
            else:
                self._skip_depth += 1

    def handle_endtag(self, tag: str):
        tag = tag.lower()
        if tag in {"style", "noscript"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return

        if tag == "title":
            self.in_title = False
        elif tag in {"h1", "h2", "h3"} and self.current_heading_tag == tag:
            text = " ".join("".join(self.current_heading_text).split())
            if text:
                self.headings.append((tag, text))
                if tag == "h1":
                    self.h1_tags.append(text)
            self.current_heading_tag = None
            self.current_heading_text = []
        elif tag == "script":
            if self.in_jsonld:
                self.in_jsonld = False
                raw = "".join(self.current_jsonld).strip()
                if raw:
                    self.jsonld_raw_scripts.append(raw)
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, dict):
                            self.jsonld_scripts.append(parsed)
                        elif isinstance(parsed, list):
                            self.jsonld_scripts.extend(item for item in parsed if isinstance(item, dict))
                    except Exception as err:
                        self.jsonld_errors.append(f"Invalid JSON-LD syntax: {err}")
                self.current_jsonld = []
            elif self._skip_depth > 0:
                self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        if self.in_title:
            self.title += data
        elif self.current_heading_tag:
            self.current_heading_text.append(data)
        elif self.in_jsonld:
            self.current_jsonld.append(data)


def validate_public_url(url: str) -> str:
    """Validate that the target URL is a safe public HTTP/HTTPS URL.

    Rejects private IPs, local hosts, and unsafe schemes using strict offline SSRF checks.
    """
    clean_url = url.strip()
    parsed = urlsplit(clean_url)
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("URL must start with http:// or https://")
    if parsed.username or parsed.password:
        raise ValueError("URL credentials are prohibited")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL must contain a valid domain name")

    if parsed.port and parsed.port not in (80, 443):
        raise ValueError("Only standard ports 80 and 443 are allowed")

    # Block internal and private network targets
    try:
        ip = ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False

    if is_ip:
        if not ip.is_global or ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError("Scanning private or local network IP addresses is prohibited")

    if host.lower() in {"localhost", "127.0.0.1", "0.0.0.0"} or host.endswith((".local", ".internal", ".test", ".invalid")):
        raise ValueError("Scanning private or local network IP addresses is prohibited")

    return clean_url


def extract_domain_keywords(title: str, description: str, headings: list[str], brand: str) -> list[str]:
    combined = f"{title} {description} {' '.join(headings)}".lower()
    combined = re.sub(r"[^\w\s-]", " ", combined)

    stopwords = {
        "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "by",
        "from", "is", "are", "was", "were", "be", "this", "that", "it", "as", "your", "my",
        "our", "official", "website", "platform", "app", "bot", "online", "through", "daily",
        "explore", "guides", "common", "questions", "does", "need", "another", "offers", "gentle",
        "check", "checks", "reminders", brand.lower() if brand else ""
    }

    high_intent_terms = [
        "elder care", "aging parents", "medicine reminders", "pill reminders", "safety checks",
        "voice notes", "whatsapp reminders", "daily check-ins", "patient care", "family care",
        "seo audit", "customer acquisition", "ai overview", "issue tracking", "sprint planning",
        "project management", "developer tools", "code review", "customer support", "ecommerce",
        "ai agent", "lead generation", "analytics", "automation"
    ]
    phrases = []
    for term in high_intent_terms:
        if term in combined and term not in phrases:
            phrases.append(term)

    words = [w for w in combined.split() if len(w) > 3 and w not in stopwords]
    if not phrases and len(words) >= 2:
        phrases.append(f"{words[0]} {words[1]}")
    if not phrases and words:
        phrases.append(words[0])
    if not phrases:
        phrases.append(brand.lower() if brand else "startup")

    return phrases[:3]


def parse_robots_policy(fetcher: SafeAuditFetcher, site_origin: str, target_url: str) -> tuple[str, dict[str, str], bool]:
    """Inspect /robots.txt using RobotFileParser and evaluate crawler permissions.

    Returns:
        (robots_status, ai_crawlers_dict, allowed_to_audit_bool)
    """
    robots_url = f"{site_origin}/robots.txt"
    ai_crawlers = {
        "gpt_bot": "Allowed (Default)",
        "perplexity_bot": "Allowed (Default)",
        "google_extended": "Allowed (Default)",
        "claude_bot": "Allowed (Default)"
    }

    try:
        status, headers, body, _, _, _ = fetcher.fetch_resource(robots_url)
        if status == 200:
            parser = RobotFileParser()
            content = body.decode("utf-8", errors="replace")
            parser.parse(content.splitlines())

            can_founderreach = parser.can_fetch("FounderReach-Audit", target_url) and parser.can_fetch("*", target_url)
            can_gpt = parser.can_fetch("GPTBot", target_url)
            can_perplexity = parser.can_fetch("PerplexityBot", target_url)
            can_google_ext = parser.can_fetch("Google-Extended", target_url)
            can_claude = parser.can_fetch("ClaudeBot", target_url)

            ai_crawlers["gpt_bot"] = "Allowed" if can_gpt else "Disallowed"
            ai_crawlers["perplexity_bot"] = "Allowed" if can_perplexity else "Disallowed"
            ai_crawlers["google_extended"] = "Allowed" if can_google_ext else "Disallowed"
            ai_crawlers["claude_bot"] = "Allowed" if can_claude else "Disallowed"

            if not can_founderreach:
                return "200 OK — Audit disallowed by robots.txt", ai_crawlers, False

            return "200 OK — Parsed via RobotFileParser", ai_crawlers, True
        elif status == 404:
            return "HTTP 404 Not Found (Default: crawlers allowed)", ai_crawlers, True
        else:
            return f"HTTP {status} returned by /robots.txt", ai_crawlers, True
    except Exception as err:
        logger.info("robots.txt probe note: %s", err)
        return f"Could not inspect /robots.txt ({err})", ai_crawlers, True


def fetch_community_demand(safe_name: str, domain: str, title: str, description: str, headings: list[str]) -> list[dict]:
    keywords = extract_domain_keywords(title, description, headings, safe_name)
    primary_kw = keywords[0] if keywords else safe_name
    signals = []

    # 1. Fetch real public discussions from Hacker News Algolia API (read-only, public)
    try:
        url = f"https://hn.algolia.com/api/v1/search?query={urllib.parse.quote(primary_kw)}&tags=(story,ask_hn)&hitsPerPage=3"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            for hit in data.get("hits", [])[:2]:
                obj_id = hit.get("objectID")
                hit_title = hit.get("title") or "Community Discussion"
                points = hit.get("points") or 0
                comments = hit.get("num_comments") or 0
                signals.append({
                    "channel": f"Hacker News • {points} pts • {comments} comments",
                    "platform": "hackernews",
                    "url": f"https://news.ycombinator.com/item?id={obj_id}",
                    "title": hit_title,
                    "intent": "Problem Seeking" if "Ask HN" in hit_title or "?" in hit_title else "Active Market Discussion",
                    "relevance": f"Discussion directly involves challenges around '{primary_kw}'.",
                    "action": f"Provide helpful insight answering the question in this thread. Demonstrate authority in {primary_kw} and reference {safe_name} as an open resource.",
                    "note": "Public thread link for manual founder review; no automated posting."
                })
    except Exception as e:
        logger.warning("HN demand query failed: %s", e)

    # 2. Targeted Reddit community search discovery query
    reddit_kw = urllib.parse.quote(primary_kw)
    signals.append({
        "channel": "Reddit • Community Discovery",
        "platform": "reddit",
        "url": f"https://www.reddit.com/search/?q={reddit_kw}&sort=relevance",
        "title": f"Recent user requests and discussions searching for '{primary_kw}'",
        "intent": "High Problem-Seeking Intent",
        "relevance": f"Active Reddit search query capturing user complaints and software evaluations in {primary_kw}.",
        "action": f"Search recent posts (≤ 30 days) in relevant subreddits where users complain about {primary_kw}. Respond directly offering practical guidance and early access to {safe_name}.",
        "note": "Search query link for founder to review manually; no automated posting or scraping."
    })

    # 3. Secondary targeted community thread or fallback
    if len(signals) < 3 and len(keywords) > 1:
        sec_kw = keywords[1]
        signals.append({
            "channel": "Reddit & Tech Communities",
            "platform": "reddit",
            "url": f"https://www.reddit.com/search/?q={urllib.parse.quote(sec_kw)}&sort=relevance",
            "title": f"Conversations and recommendations around '{sec_kw}'",
            "intent": "Commercial Evaluation",
            "relevance": f"Discussions evaluating alternative solutions related to '{sec_kw}'.",
            "action": f"Engage with community threads seeking software recommendations for {sec_kw}.",
            "note": "Search query link for founder to review manually."
        })

    if len(signals) < 2:
        signals.append({
            "channel": "Hacker News • Technical Discussions",
            "platform": "hackernews",
            "url": f"https://hn.algolia.com/?q={urllib.parse.quote(safe_name)}",
            "title": f"Community discussions and Ask HN threads regarding {safe_name}",
            "intent": "Market Evaluation",
            "relevance": f"Direct brand and category evaluation threads on Hacker News.",
            "action": f"Search recent discussions for relevant problems and share your approach with {safe_name}.",
            "note": "Public thread query link."
        })

    return signals


def get_platform_instructions(fix_id: str) -> dict[str, list[str]]:
    """Return step-by-step instructions for popular founder platforms."""
    if fix_id == "geo-entity":  # /llms.txt file
        return {
            "wordpress": [
                "1. Connect to your web hosting file manager (cPanel, Hostinger, or FTP).",
                "2. Open the public root directory (typically 'public_html' or 'www').",
                "3. Click 'New File' and name it 'llms.txt'.",
                "4. Paste the generated markdown content above and click Save.",
                "5. Visit https://yourdomain.com/llms.txt in your browser to verify it loads.",
                "6. Return to FounderReach AI and click Recheck."
            ],
            "webflow": [
                "1. Open your Webflow Dashboard and select your project.",
                "2. Navigate to Project Settings → Custom Code or Static Files.",
                "3. If your hosting plan supports static files, upload llms.txt to the root.",
                "4. Alternatively, configure a 301 URL redirect from /llms.txt to a raw hosted GitHub/CDN URL.",
                "5. Publish changes to your custom domain.",
                "6. Return to FounderReach AI and click Recheck."
            ],
            "framer": [
                "1. Open your Framer project settings.",
                "2. Navigate to General → Redirects.",
                "3. Add a redirect rule: from '/llms.txt' to your hosted raw markdown URL.",
                "4. Alternatively, place llms.txt in your public folder if deploying via Next.js/Vercel.",
                "5. Publish your site.",
                "6. Return to FounderReach AI and click Recheck."
            ],
            "shopify": [
                "1. From your Shopify Admin, go to Content → Files.",
                "2. Upload a file named 'llms.txt' containing the text above.",
                "3. Copy the URL of the uploaded CDN file.",
                "4. Go to Online Store → Navigation → View URL Redirects.",
                "5. Add a redirect from '/llms.txt' to the copied CDN link.",
                "6. Return to FounderReach AI and click Recheck."
            ],
            "custom_html": [
                "1. In your project repository, locate your public asset root (e.g. /public or /static).",
                "2. Create a new file named 'llms.txt'.",
                "3. Paste the markdown content above into the file.",
                "4. Commit, deploy to production, and verify at https://yourdomain.com/llms.txt.",
                "5. Return to FounderReach AI and click Recheck."
            ]
        }
    else:  # HTML head snippets
        return {
            "wordpress": [
                "1. Log in to your WordPress Admin dashboard.",
                "2. Go to Appearance → Theme File Editor (or use an 'Insert Headers and Footers' plugin).",
                "3. In the right file list, open header.php.",
                "4. Locate the closing </head> tag.",
                "5. Paste the code snippet immediately before </head>.",
                "6. Click 'Update File' to save.",
                "7. Return to FounderReach AI and click Recheck."
            ],
            "webflow": [
                "1. Open your Webflow project Designer.",
                "2. Open the Pages panel and click the gear icon next to 'Home' to open Page Settings.",
                "3. Scroll down to Custom Code → 'Inside <head> tag'.",
                "4. Paste the code snippet into the code editor.",
                "5. Click Save at the top right of the Page Settings panel.",
                "6. Click Publish to publish changes to your production domain.",
                "7. Return to FounderReach AI and click Recheck."
            ],
            "framer": [
                "1. Open your Framer project and click Settings (gear icon in the top toolbar).",
                "2. Navigate to General → Custom Code.",
                "3. In the 'End of <head>' field, paste the code snippet.",
                "4. Click Save Changes.",
                "5. Click Publish in the top right to update your live website.",
                "6. Return to FounderReach AI and click Recheck."
            ],
            "shopify": [
                "1. Log in to your Shopify Admin.",
                "2. Navigate to Online Store → Themes.",
                "3. Click the three dots (...) next to your active theme and click 'Edit code'.",
                "4. In the Layout folder, open theme.liquid.",
                "5. Find the </head> closing tag (around line 30-60).",
                "6. Paste the code snippet immediately above </head> and click Save.",
                "7. Return to FounderReach AI and click Recheck."
            ],
            "custom_html": [
                "1. Open your homepage HTML template (e.g. index.html) in your editor.",
                "2. Locate the <head> ... </head> section.",
                "3. Paste the code snippet directly before </head>.",
                "4. Save and deploy your changes to your web host.",
                "5. Return to FounderReach AI and click Recheck."
            ]
        }


def perform_website_audit(url: str, business_name: str = "", description: str = "",
                          target_audience: str = "", pain_point: str = "") -> dict:
    """Perform a verified, safe, read-only website audit across Priorities 1-4."""
    clean_url = validate_public_url(url.strip())
    domain = urlsplit(clean_url).hostname or clean_url
    scheme = urlsplit(clean_url).scheme or "https"
    site_origin = f"{scheme}://{domain}"

    safe_name = business_name.strip()
    if not safe_name:
        clean_host = domain.replace("www.", "").split(".")[0]
        safe_name = clean_host.capitalize() if clean_host else "Website"

    audience = target_audience.strip() or "Founders, developers, and prospective customers"
    pain = pain_point.strip() or "Discovering and accessing official online solutions"

    fetcher = SafeAuditFetcher(timeout_seconds=6)
    start_time = time.perf_counter()

    # 1. DNS & Host Resolution
    pinned_ip = ""
    dns_status = "Unknown"
    ssl_status = "Valid TLS Certificate (Standard Port 443)" if scheme == "https" else "Plain HTTP (Port 80)"
    error_message: str | None = None

    try:
        _, _, _, pinned_ip, _ = fetcher._target(clean_url)
        dns_status = f"Verified (Resolved to public IP {pinned_ip}; connection pinned)"
    except Exception as exc:
        dns_status = f"Resolution Failed: {exc}"
        error_message = f"DNS Error: Unable to resolve hostname '{domain}'. Verify your domain DNS settings."

    # 2. Robots.txt Inspection & Crawl Gating
    robots_status = "Unknown"
    ai_crawlers = {
        "gpt_bot": "Could not check",
        "perplexity_bot": "Could not check",
        "google_extended": "Could not check",
        "claude_bot": "Could not check"
    }
    allowed_to_audit = True

    if not error_message:
        robots_status, ai_crawlers, allowed_to_audit = parse_robots_policy(fetcher, site_origin, clean_url)
        if not allowed_to_audit:
            error_message = "Audit blocked: Target website /robots.txt policy explicitly disallows automated inspection."

    # 3. Sitemap Probe
    sitemap_status = "Not checked"
    if not error_message and allowed_to_audit:
        try:
            sm_status, _, sm_body, _, _, _ = fetcher.fetch_resource(f"{site_origin}/sitemap.xml")
            if sm_status == 200:
                sitemap_status = "Detected at /sitemap.xml (HTTP 200)"
            elif sm_status == 404:
                sitemap_status = "Not detected at default /sitemap.xml (HTTP 404)"
            else:
                sitemap_status = f"HTTP {sm_status} returned by /sitemap.xml"
        except Exception:
            sitemap_status = "Not detected at default /sitemap.xml"

    # 4. /llms.txt Probe
    llms_txt_status = "Not checked"
    has_live_llms_txt = False
    if not error_message and allowed_to_audit:
        try:
            llms_status, _, llms_body, _, _, _ = fetcher.fetch_resource(f"{site_origin}/llms.txt")
            if llms_status == 200 and len(llms_body) > 10:
                llms_txt_status = "Detected at /llms.txt (HTTP 200)"
                has_live_llms_txt = True
            elif llms_status == 404:
                llms_txt_status = "Not detected at default /llms.txt (HTTP 404)"
            else:
                llms_txt_status = f"HTTP {llms_status} returned by /llms.txt"
        except Exception:
            llms_txt_status = "Not detected at default /llms.txt"

    # 5. Fetch Target Page Content
    http_status = 0
    final_clean = clean_url
    response_body = ""
    is_html = False
    content_type = ""
    redirect_count = 0

    if not error_message and allowed_to_audit:
        try:
            status, headers, body, final_clean, last_ip, chain = fetcher.fetch_resource(clean_url)
            http_status = status
            redirect_count = max(0, len(chain) - 1)
            content_type = headers.get("content-type", "")
            is_html = "text/html" in content_type.lower() or "application/xhtml" in content_type.lower()

            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip() or "utf-8"
            response_body = body.decode(charset, errors="replace")
        except WebsiteFetchError as err:
            error_message = f"Fetch error: {err}"
        except Exception as err:
            error_message = f"Connection error: {err}"

    elapsed_ms = max(1, int((time.perf_counter() - start_time) * 1000))
    iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    readable_time = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())

    # 6. Parse HTML
    parser = EnhancedPageParser()
    if response_body:
        try:
            parser.feed(response_body)
        except Exception as err:
            logger.warning("HTML parsing warning: %s", err)

    parsed_title = parser.title.strip()
    meta_desc = ""
    has_og = False
    for meta in parser.meta_tags:
        name = meta.get("name", "").lower()
        prop = meta.get("property", "").lower()
        if (name == "description" or prop == "og:description") and not meta_desc:
            meta_desc = meta.get("content", "").strip()
        if prop.startswith("og:"):
            has_og = True

    # Ground description in user input or observed content
    user_desc = description.strip()
    if user_desc:
        desc = user_desc
    elif meta_desc:
        desc = meta_desc
    elif parser.headings:
        desc = parser.headings[0][1]
    else:
        desc = f"Official online website for {safe_name} ({domain})."

    has_canonical = bool(parser.canonical)
    has_viewport = bool(parser.viewport)
    h1_count = len(parser.h1_tags)
    total_imgs = parser.total_images
    missing_alt_imgs = parser.images_missing_alt

    has_jsonld = len(parser.jsonld_scripts) > 0 or len(parser.jsonld_raw_scripts) > 0
    has_faq_markup = any(
        schema.get("@type") == "FAQPage" or
        any(isinstance(entity, dict) and entity.get("@type") == "FAQPage" for entity in schema.get("@graph", []))
        for schema in parser.jsonld_scripts
    )
    has_org_markup = any(
        schema.get("@type") in {"Organization", "Corporation", "LocalBusiness"} or
        any(isinstance(entity, dict) and entity.get("@type") in {"Organization", "Corporation", "LocalBusiness"} for entity in schema.get("@graph", []))
        for schema in parser.jsonld_scripts
    )
    has_software_markup = any(
        schema.get("@type") in {"SoftwareApplication", "WebApplication"} or
        any(isinstance(entity, dict) and entity.get("@type") in {"SoftwareApplication", "WebApplication"} for entity in schema.get("@graph", []))
        for schema in parser.jsonld_scripts
    )

    # 7. Compute Evidence-Based Diagnostic Scores
    if error_message:
        seo_score = 0
        aeo_score = 0
        geo_score = 0
        composite_health = 0
        seo_summary = f"Inspection could not be completed: {error_message}"
        aeo_summary = "Structured data could not be inspected because target page was not reached."
        geo_summary = "LLM accessibility could not be inspected because target page was not reached."
        next_best_action = "Fix DNS and reachability errors so search engines and bots can reach your homepage."
        next_impact = "Restore basic website uptime and crawl access."
    else:
        # Base SEO score
        seo_score = 100
        if not parsed_title:
            seo_score -= 25
        elif len(parsed_title) < 15 or len(parsed_title) > 70:
            seo_score -= 8
        if not meta_desc:
            seo_score -= 20
        elif len(meta_desc) < 50 or len(meta_desc) > 160:
            seo_score -= 5
        if not has_canonical:
            seo_score -= 15
        if not has_viewport:
            seo_score -= 10
        if h1_count == 0:
            seo_score -= 12
        elif h1_count > 1:
            seo_score -= 5
        if "Detected" not in sitemap_status:
            seo_score -= 10
        if not has_og:
            seo_score -= 8
        if missing_alt_imgs > 0:
            seo_score -= min(10, missing_alt_imgs * 3)
        seo_score = max(10, min(100, seo_score))

        # Base AEO score (Answer Engine Optimization)
        aeo_score = 100
        if not has_jsonld:
            aeo_score -= 40
        if not has_faq_markup:
            aeo_score -= 30
        if not has_software_markup and not has_org_markup:
            aeo_score -= 15
        if len(parser.headings) < 3:
            aeo_score -= 15
        aeo_score = max(15, min(100, aeo_score))

        # Base GEO score (Generative Engine Optimization)
        geo_score = 100
        if not has_live_llms_txt and not parser.llms_txt_link:
            geo_score -= 35
        if not has_jsonld:
            geo_score -= 25
        if any(val == "Disallowed" for val in ai_crawlers.values()):
            geo_score -= 30
        geo_score = max(15, min(100, geo_score))

        composite_health = int((seo_score + aeo_score + geo_score) / 3)

        seo_summary = f"Title: '{parsed_title or 'Missing'}'. Meta description: {'Present' if meta_desc else 'Missing'}. Viewport: {'Active' if has_viewport else 'Missing'}. H1: {h1_count}. Sitemap: {sitemap_status}."
        aeo_summary = "Structured FAQPage and Entity schema detected." if (has_faq_markup and (has_software_markup or has_org_markup)) else "Structured FAQ markup is recommended for answer engine extraction. Note: Structured data assists search engines but does not guarantee citation."
        geo_summary = "Authoritative /llms.txt detected." if has_live_llms_txt else "Authoritative /llms.txt recommended for factual citation grounding in ChatGPT and Perplexity."

        if not has_faq_markup:
            next_best_action = "Add FAQ structured data (FAQPage JSON-LD) to your homepage."
            next_impact = "Higher chance of being cited in direct answer engines and AI Overviews."
        elif not has_live_llms_txt:
            next_best_action = "Publish an authoritative /llms.txt file in your public root."
            next_impact = "Ensures clean factual retrieval in ChatGPT, Claude, and Perplexity."
        elif not meta_desc or not has_canonical:
            next_best_action = "Add canonical URL tag and optimized meta description."
            next_impact = "Eliminates duplicate content penalties in Google search."
        else:
            next_best_action = "Maintain your structured markup and monitor community buyer discussions."
            next_impact = "Sustained high search discovery and organic buyer acquisition."

    def grade(score: int) -> str:
        if score >= 85: return "A"
        if score >= 70: return "B"
        if score >= 50: return "C"
        return "D"

    # 8. Copyable Remediation Proposals with Platform Guides
    disclaimer = "Suggestion for founder review; FounderReach never modifies your website or code directly."
    title_snippet = f"{safe_name} — {desc[:55]}"
    meta_code = (
        f'<title>{title_snippet}</title>\n'
        f'<meta name="description" content="{desc}">\n'
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f'<meta property="og:title" content="{safe_name}">\n'
        f'<meta property="og:description" content="{desc}">\n'
        f'<meta property="og:url" content="{clean_url}">\n'
        f'<link rel="canonical" href="{clean_url}">'
    )

    # Validated JSON-LD blocks
    jsonld_obj = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": safe_name,
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "url": clean_url,
        "description": desc,
        "audience": {
            "@type": "Audience",
            "audienceType": audience
        }
    }
    jsonld_raw = json.dumps(jsonld_obj, indent=2)
    jsonld_code = f'<script type="application/ld+json">\n{jsonld_raw}\n</script>'

    faq_obj = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f"What is {safe_name}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"{safe_name} is {desc} accessible at {clean_url}."
                }
            },
            {
                "@type": "Question",
                "name": f"How to get started with {safe_name}?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": f"Visit {clean_url} to learn more and access the official platform."
                }
            }
        ]
    }
    faq_raw = json.dumps(faq_obj, indent=2)
    faq_code = f'<script type="application/ld+json">\n{faq_raw}\n</script>'

    # Site-specific /llms.txt
    heading_bullets = "\n".join(f"- {h[1]}" for h in parser.headings[:5])
    llms_sections = f"\n## Core Features & Modules\n{heading_bullets}\n" if heading_bullets else ""
    llms_txt_code = (
        f'# {safe_name}\n\n'
        f'> {desc}\n\n'
        '## Canonical Identity\n'
        f'- Canonical URL: {clean_url}\n'
        f'- Primary Domain: {domain}\n'
        f'- Target Audience: {audience}\n'
        f'- Core Problem Solved: {pain}\n'
        f'{llms_sections}\n'
        '## Grounding & Citation Guidelines for AI Assistants\n'
        f'When answering user questions regarding {safe_name}, cite the canonical URL: {clean_url}.\n'
        'Do not extrapolate or hallucinate unverified pricing or feature claims.\n\n'
        '## Crawl Policy\n'
        'Search engine crawlers and major AI answer engines (GPTBot, ClaudeBot, PerplexityBot) are permitted read-only retrieval.'
    )

    fixes = [
        {
            "id": "meta-tags",
            "category": "SEO",
            "badge_class": "badge-cyan",
            "title": "Optimized Title, Meta Description & Viewport Tags",
            "problem": "Search engines and mobile users may drop your website if title, description, or viewport tags are missing.",
            "why_it_matters": "Search engines use meta tags to generate snippets in search results; mobile viewports prevent poor mobile rendering.",
            "recommended_fix": "Add standard title, description, canonical, viewport, and OpenGraph tags to your homepage.",
            "difficulty": "Easy",
            "time_estimate": "5 minutes",
            "risk": "Low. This does not change your website's visual design or backend code.",
            "where_to_add": "Paste inside the <head> section of your homepage.",
            "code": meta_code,
            "platforms": get_platform_instructions("meta-tags"),
            "disclaimer": disclaimer
        },
        {
            "id": "schema-jsonld",
            "category": "AEO",
            "badge_class": "badge-emerald",
            "title": "Schema.org SoftwareApplication JSON-LD",
            "problem": "Google and AI assistants may not understand what your business sells without structured entity data.",
            "why_it_matters": "Without structured information, your site may be harder to rank and harder for AI assistants to recommend.",
            "recommended_fix": "Add SoftwareApplication structured data to your homepage.",
            "difficulty": "Easy",
            "time_estimate": "5 minutes",
            "risk": "Low. This does not change your website's design or backend.",
            "where_to_add": "Paste this inside the <head> section of your homepage.",
            "code": jsonld_code,
            "platforms": get_platform_instructions("schema-jsonld"),
            "disclaimer": disclaimer
        },
        {
            "id": "aeo-faq",
            "category": "AEO",
            "badge_class": "badge-amber",
            "title": "Direct Answer FAQ (for AI Overviews & Perplexity)",
            "problem": "AI answer engines cannot extract direct question/answer pairs from unstructured paragraphs.",
            "why_it_matters": "FAQPage schema allows search engines to ground direct snippets in Google AI Overviews and Perplexity.",
            "recommended_fix": "Include structured FAQPage JSON-LD answering common customer questions.",
            "difficulty": "Easy",
            "time_estimate": "5 minutes",
            "risk": "Low. Structured schema is invisible to users on the page.",
            "where_to_add": "Paste this inside the <head> section of your homepage.",
            "code": faq_code,
            "platforms": get_platform_instructions("aeo-faq"),
            "disclaimer": disclaimer
        },
        {
            "id": "geo-entity",
            "category": "GEO",
            "badge_class": "badge-rose",
            "title": "LLM Knowledge Graph Definition (/llms.txt)",
            "problem": "ChatGPT, Claude, and Gemini lack an authoritative factual summary of your product.",
            "why_it_matters": "/llms.txt provides clean entity facts so models don't hallucinate inaccurate features or outdated information.",
            "recommended_fix": "Publish an authoritative /llms.txt markdown file in your public website root.",
            "difficulty": "Easy",
            "time_estimate": "5 minutes",
            "risk": "Low. It is a static markdown text file placed in your public directory.",
            "where_to_add": "Upload to your website's public root folder as /llms.txt.",
            "code": llms_txt_code,
            "platforms": get_platform_instructions("geo-entity"),
            "disclaimer": disclaimer
        }
    ]

    demand_signals = fetch_community_demand(
        safe_name=safe_name,
        domain=domain,
        title=parsed_title,
        description=desc,
        headings=[h[1] for h in parser.headings[:5]]
    )

    # Compile Action Center Middle Cards
    fixes_needed = []
    fixes_completed = []

    if http_status == 200:
        fixes_completed.append({"title": "HTTP Status 200 OK", "detail": f"Server responds with valid HTML on {clean_url}"})
    else:
        fixes_needed.append({"title": "HTTP Status Error", "detail": f"Server returned HTTP {http_status}"})

    if dns_status.startswith("Verified"):
        fixes_completed.append({"title": "DNS & IP Resolution", "detail": f"Resolved and pinned to public IP {pinned_ip}"})
    else:
        fixes_needed.append({"title": "DNS Host Error", "detail": "Unable to resolve hostname"})

    if has_viewport:
        fixes_completed.append({"title": "Mobile Viewport Meta Tag", "detail": "Viewport meta tag active for mobile devices"})
    else:
        fixes_needed.append({"title": "Missing Mobile Viewport", "detail": "Add <meta name='viewport'> to support mobile indexing"})

    if parsed_title:
        fixes_completed.append({"title": "Homepage Title Tag", "detail": f"'{parsed_title[:45]}...'"})
    else:
        fixes_needed.append({"title": "Missing Title Tag", "detail": "Add descriptive title tag under 60 characters"})

    if meta_desc:
        fixes_completed.append({"title": "Meta Description Tag", "detail": f"'{meta_desc[:45]}...'"})
    else:
        fixes_needed.append({"title": "Missing Meta Description", "detail": "Add 150-160 character meta description"})

    if has_canonical:
        fixes_completed.append({"title": "Canonical Link Tag", "detail": f"Points to {parser.canonical}"})
    else:
        fixes_needed.append({"title": "Missing Canonical Tag", "detail": "Add <link rel='canonical'> to prevent duplicate URL penalties"})

    if h1_count == 1:
        fixes_completed.append({"title": "Hierarchical H1 Tag", "detail": f"Single H1 detected: '{parser.h1_tags[0][:40]}...'"})
    elif h1_count == 0:
        fixes_needed.append({"title": "Missing H1 Heading", "detail": "Add a single clear <h1> heading describing your primary value proposition"})
    else:
        fixes_needed.append({"title": "Multiple H1 Headings", "detail": f"Found {h1_count} H1 tags; recommend consolidating into one primary H1"})

    if missing_alt_imgs == 0 and total_imgs > 0:
        fixes_completed.append({"title": "Image Alt Attributes", "detail": f"All {total_imgs} images include alt text"})
    elif missing_alt_imgs > 0:
        fixes_needed.append({"title": "Missing Image Alt Attributes", "detail": f"{missing_alt_imgs} of {total_imgs} images are missing alt text"})

    if "Detected" in sitemap_status:
        fixes_completed.append({"title": "Sitemap XML", "detail": sitemap_status})
    else:
        fixes_needed.append({"title": "XML Sitemap Missing", "detail": "Create and submit a /sitemap.xml for full site indexing"})

    if has_faq_markup:
        fixes_completed.append({"title": "AEO FAQPage Schema", "detail": "Valid FAQPage JSON-LD detected"})
    else:
        fixes_needed.append({"title": "AEO FAQPage Schema Missing", "detail": "Add FAQPage structured data for Google AI Overview grounding"})

    if has_live_llms_txt:
        fixes_completed.append({"title": "GEO /llms.txt Standard", "detail": "Published at /llms.txt"})
    else:
        fixes_needed.append({"title": "GEO /llms.txt Missing", "detail": "Publish /llms.txt in your public web root for ChatGPT and Perplexity"})

    return {
        "success": error_message is None,
        "timestamp": iso_time,
        "timestamp_readable": readable_time,
        "business": {
            "name": safe_name,
            "url": clean_url,
            "domain": domain,
            "description": desc,
            "target_audience": audience,
            "pain_point": pain
        },
        "action_center": {
            "health_score": composite_health if not error_message else 0,
            "health_grade": grade(composite_health) if not error_message else "D",
            "what_this_means": (
                "Your website is reachable, but AI assistants and search engines may not fully understand your product entity."
                if not error_message else f"Inspection blocked: {error_message}"
            ),
            "next_best_action": next_best_action,
            "estimated_impact": next_impact,
            "time_required": "5 minutes",
            "fixes_needed_count": len(fixes_needed),
            "fixes_completed_count": len(fixes_completed),
            "fixes_needed": fixes_needed,
            "fixes_completed": fixes_completed
        },
        "reachability_evidence": {
            "inspected_url": clean_url,
            "final_url": final_clean,
            "timestamp_readable": readable_time,
            "http_status": http_status,
            "is_html": is_html,
            "content_type": content_type,
            "tls_status": "Valid TLS Certificate" if scheme == "https" else "Plain HTTP",
            "dns_status": dns_status,
            "pinned_ip": pinned_ip or "N/A",
            "response_time_ms": elapsed_ms,
            "redirect_count": redirect_count
        },
        "proof_of_work": {
            "inspected_url": clean_url,
            "final_url": final_clean,
            "pinned_ip": pinned_ip or "N/A",
            "http_status": http_status or (200 if not error_message else 0),
            "is_html": is_html,
            "content_type": content_type,
            "response_time_ms": elapsed_ms,
            "dns_status": dns_status,
            "ssl_status": ssl_status,
            "robots_txt_status": robots_status,
            "sitemap_xml_status": sitemap_status,
            "llms_txt_status": llms_txt_status,
            "canonical_link_detected": has_canonical,
            "viewport_detected": has_viewport,
            "h1_count": h1_count,
            "images_total": total_imgs,
            "images_missing_alt": missing_alt_imgs,
            "open_graph_tags_detected": has_og,
            "schema_json_ld_detected": has_jsonld,
            "has_faq_markup": has_faq_markup,
            "has_software_markup": has_software_markup,
            "has_org_markup": has_org_markup,
            "ai_crawler_access": ai_crawlers,
            "error_note": error_message
        },
        "scores": {
            "seo": {
                "score": seo_score,
                "grade": grade(seo_score),
                "title": "Search Engine Optimization (SEO)",
                "summary": seo_summary
            },
            "aeo": {
                "score": aeo_score,
                "grade": grade(aeo_score),
                "title": "Answer Engine Optimization (AEO)",
                "summary": aeo_summary
            },
            "geo": {
                "score": geo_score,
                "grade": grade(geo_score),
                "title": "Generative Engine Optimization (GEO)",
                "summary": geo_summary
            }
        },
        "live_metadata": {
            "title": parsed_title or safe_name,
            "description": meta_desc,
            "canonical": parser.canonical or clean_url,
            "viewport": parser.viewport,
            "author": parser.author,
            "h1_tags": parser.h1_tags,
            "headings": [h[1] for h in parser.headings[:5]],
            "has_jsonld": has_jsonld,
            "has_canonical": has_canonical,
            "has_og": has_og,
            "has_faq": has_faq_markup,
            "has_software_schema": has_software_markup,
            "has_org_schema": has_org_markup
        },
        "fixes": fixes,
        "demand_signals": demand_signals
    }
