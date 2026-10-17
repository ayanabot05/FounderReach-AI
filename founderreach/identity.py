"""Stable local identities. Business identity is independent of display name."""
import hashlib
import re


def business_id(identifier: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", identifier):
        raise ValueError("Business identifier must be a stable lowercase slug")
    return identifier


def source_id(platform: str, native_id: str) -> str:
    platform_key = re.sub(r"[^a-z0-9]+", "-", platform.lower()).strip("-")
    if not platform_key or not native_id or len(native_id) > 200:
        raise ValueError("Source platform and native ID are required")
    return f"{platform_key}:{native_id}"


def opportunity_id(business: str, source: str) -> str:
    return hashlib.sha256(f"founderreach:v1:{business_id(business)}:{source}".encode()).hexdigest()[:24]
