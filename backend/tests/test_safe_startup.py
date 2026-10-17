"""The test guard must reject client paths before a file opener is called."""
from pathlib import Path

import pytest

from _safe_bootstrap import _ROOT, _guard_open, _prohibited
from founderreach.profiles import load_profile


@pytest.mark.parametrize("path", [
    _ROOT / "profiles" / "client.json",
    _ROOT / "reports" / "INDEPENDENT_LABELS.json",
    _ROOT / "evals" / "m4_human_comparison.json",
    _ROOT / "data" / "client.db",
    _ROOT / ".env",
])
def test_client_and_credential_paths_are_blocked_before_open(path):
    reached = []
    guarded = _guard_open(lambda *args, **kwargs: reached.append(True))
    assert _prohibited(path)
    with pytest.raises(PermissionError, match="Prohibited"):
        guarded(path)
    assert reached == []


def test_synthetic_careflow_profile_name_resolves_to_synthetic_test_double():
    profile = load_profile("careflow")
    assert profile.name == "Synthetic Care"
    assert str(profile.website) == "https://care-fixture.example.com/"
