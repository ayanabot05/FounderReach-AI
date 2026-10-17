"""Keep human comparison labels distinct from fixture expectations."""
from pathlib import Path
import json


CHANNELS = {"owned_website", "owned_social", "community_research", "no_action"}


def compare_human_labels(decisions: dict[str, str], label_file: Path) -> dict:
    cases = json.loads(Path(label_file).read_text(encoding="utf-8"))
    labeled = []
    pending = []
    for row in cases:
        case_id = row["case_id"]
        label = row.get("human_label")
        if label is None:
            pending.append(case_id)
            continue
        if row.get("label_origin") != "human" or label not in CHANNELS:
            raise ValueError("Comparison label lacks explicit human provenance")
        if case_id not in decisions:
            raise ValueError("Missing decision for labeled case")
        labeled.append({"case_id": case_id, "human_label": label,
                        "engine_channel": decisions[case_id],
                        "agreement": label == decisions[case_id]})
    return {"labeled_count": len(labeled), "pending_case_ids": pending,
            "agreement_count": sum(x["agreement"] for x in labeled),
            "disagreements": [x for x in labeled if not x["agreement"]],
            "comparison": labeled,
            "agreement_rate": (sum(x["agreement"] for x in labeled) / len(labeled)) if labeled else None}
