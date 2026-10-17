"""Pattern checks for some identifiers; human minimization is still required."""
import re


_EMAIL = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
_HANDLE = re.compile(r"(?<!\w)@[A-Za-z0-9_]{2,}")


def require_minimized_text(*values: str | None) -> None:
    """Reject detected email, phone and handle patterns, not all personal data."""
    for value in values:
        if value and any(pattern.search(value) for pattern in (_EMAIL, _PHONE, _HANDLE)):
            raise ValueError("Research text contains a personal identifier; minimize it before persistence")
