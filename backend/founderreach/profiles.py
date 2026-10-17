"""Local founder-confirmed profiles. Suggested profiles cannot drive the engine."""
import json
from pathlib import Path
from founderreach.models import ProductProfile

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"


def load_profile(identifier: str, directory: Path = PROFILE_DIR) -> ProductProfile:
    if not identifier or Path(identifier).name != identifier or not identifier.replace("-", "").replace("_", "").isalnum():
        raise ValueError("Invalid profile identifier")
    profile = ProductProfile.model_validate_json((directory / f"{identifier}.json").read_text(encoding="utf-8"))
    if profile.identifier != identifier or not profile.confirmed:
        raise ValueError("Only matching founder-confirmed profiles may drive decisions")
    return profile
