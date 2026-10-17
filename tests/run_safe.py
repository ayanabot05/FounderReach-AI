"""Run the local suite with guards installed before pytest imports."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _safe_bootstrap import install

install()

import pytest

raise SystemExit(pytest.main(["tests", *sys.argv[1:]]))
