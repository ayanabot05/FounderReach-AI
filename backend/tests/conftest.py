"""Fail closed before test-module imports, including direct pytest runs."""
from _safe_bootstrap import install

install()
