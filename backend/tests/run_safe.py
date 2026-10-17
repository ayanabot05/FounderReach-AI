"""Run the local suite with guards installed before pytest imports."""
import sys
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TESTS_DIR.parent
for path_entry in (str(TESTS_DIR), str(BACKEND_DIR)):
    if path_entry not in sys.path:
        sys.path.insert(0, path_entry)
from _safe_bootstrap import install

install()

import pytest

raise SystemExit(pytest.main([str(TESTS_DIR), *sys.argv[1:]]))
