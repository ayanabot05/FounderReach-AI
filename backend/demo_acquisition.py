"""Offline CareFlow decision demo. Writes a local artifact; performs no external action."""

from pathlib import Path
from founderreach.acquisition import build_careflow_decision


def main():
    root = Path(__file__).resolve().parent
    run = build_careflow_decision(str(root / "reports" / "INDEPENDENT_LABELS.json"))
    # Keep the assisted recommendation in a local artifact until the founder
    # completes the baseline exercise. No action is prepared or approved.
    output = root / "data" / "careflow_decision_local_demo.json"
    run.export_local(str(output))
    print(f"Offline decision artifact: {output}")
    print(f"Candidates: {len(run.experiments)}; positive research examples: {len(run.evidence_audit['positive_problem_examples'])}")
    print("State: baseline pending; no approval, publication, contact, production write, or paid call")


if __name__ == "__main__":
    main()
