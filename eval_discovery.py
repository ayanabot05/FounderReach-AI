"""Local, non-persistent AYANA discovery diagnostic.

Uses the same dated HN pipeline as the CLI. No production database writes or
community reply drafts are made by this script.
"""
import json

from founderreach.engine import OpportunityFinderEngine
from founderreach.profiles import load_profile


if __name__ == "__main__":
    profile = load_profile("ayana")
    results = OpportunityFinderEngine().find_opportunities(
        profile, min_score=60, limit=30, actionable_only=False, persist=False)
    print(json.dumps([result.model_dump(mode="json") for result in results], indent=2))
