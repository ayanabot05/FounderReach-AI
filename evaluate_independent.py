"""Offline, reproducible text-intent challenge evaluation; no network or paid API."""
import json
from pathlib import Path
from founderreach.engine import AYANA_PROFILE
from founderreach.validation.intent import intent_classifier


def evaluate(rows):
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    details = []
    for row in rows:
        predicted, _, _ = intent_classifier.extract_direct_evidence(row["text"], AYANA_PROFILE)
        actual = row["label"] == "POTENTIAL_CUSTOMER_INTENT"
        key = "tp" if actual and predicted else "fn" if actual else "fp" if predicted else "tn"
        counts[key] += 1
        details.append({"id": row["id"], "actual": actual, "predicted": predicted, "outcome": key})
    counts["precision"] = counts["tp"] / (counts["tp"] + counts["fp"]) if counts["tp"] + counts["fp"] else None
    counts["recall"] = counts["tp"] / (counts["tp"] + counts["fn"]) if counts["tp"] + counts["fn"] else None
    return {"scope": "hand-labeled text intent only, not live end-to-end outreach", "counts": counts, "details": details}


if __name__ == "__main__":
    path = Path(__file__).parent / "reports" / "INDEPENDENT_LABELS.json"
    print(json.dumps(evaluate(json.loads(path.read_text(encoding="utf-8"))), indent=2))
