import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import base64
import hashlib

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from founderreach.acquisition import Approval, Outcome, PreflightAttestation, build_ayana_decision
from founderreach.approval_gate import approval_message, preflight_message
import founderreach.approval_gate as gate


import tempfile
from _synthetic_profiles import CARE_SYNTHETIC_LABELS


def decision():
    labels_file = Path(tempfile.gettempdir()) / "founderreach_synthetic_labels.json"
    labels_file.write_text(json.dumps(CARE_SYNTHETIC_LABELS), encoding="utf-8")
    return build_ayana_decision(str(labels_file))


def baseline(tmp_path):
    file = tmp_path / "completed_baseline.json"
    file.write_text(json.dumps({"founder_id": "A", "start_time": "10:00", "stop_time": "10:45",
        "active_minutes": 45, "sources": ["manual source"], "selected_action": "Manual choice",
        "draft_outline": "Outline", "cta": "CTA", "measurement_plan": "28 days",
        "seen_prior_recommendation": "yes"}), encoding="utf-8")
    return file


def signed_gate(monkeypatch, tmp_path, action):
    ceo = Ed25519PrivateKey.generate()
    verifier = Ed25519PrivateKey.generate()
    public = lambda key: base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    monkeypatch.setenv('FOUNDERREACH_CEO_PUBLIC_KEY', public(ceo))
    monkeypatch.setenv('FOUNDERREACH_PREFLIGHT_PUBLIC_KEY', public(verifier))
    monkeypatch.setattr(gate, 'ROOT', tmp_path)
    now = datetime.now(timezone.utc)
    approval = Approval(action.version, now.isoformat(), (now + timedelta(hours=1)).isoformat(), '')
    approval = Approval(approval.version, approval.approved_at, approval.expires_at,
                        base64.b64encode(ceo.sign(approval_message(approval))).decode())
    evidence = tmp_path / 'readonly-preflight.json'
    evidence.write_text('{"read_only": true}', encoding='utf-8')
    check = {'result': 'PASS', 'artifact': evidence.name, 'sha256': hashlib.sha256(evidence.read_bytes()).hexdigest()}
    preflight = PreflightAttestation(action.version, now.isoformat(),
                                    {name: check for name in gate.CHECKS}, '')
    preflight = PreflightAttestation(preflight.version, preflight.observed_at, preflight.checks,
                                    base64.b64encode(verifier.sign(preflight_message(preflight))).decode())
    return approval, preflight, ceo, verifier, evidence


def test_three_ranked_channels_use_problem_labels_without_outreach():
    run = decision()
    assert [e.rank for e in run.experiments] == [1, 2, 3]
    assert len({e.channel for e in run.experiments}) == 3
    assert len(run.evidence_audit["positive_problem_examples"]) == 2
    assert all(not e["outreach_eligible"] for e in run.evidence_audit["positive_problem_examples"])
    assert all(e.planned_cost_inr == 0 for e in run.experiments)
    assert run.approval is None and run.action is None


def test_baseline_required_and_blank_template_rejected(tmp_path):
    run = decision()
    with pytest.raises(PermissionError):
        run.prepare_action("Copy", "https://www.ayanabott.com/")
    blank_md = tmp_path / "MANUAL_BASELINE_TEMPLATE.md"
    blank_md.write_text("# Template", encoding="utf-8")
    with pytest.raises(ValueError):
        run.freeze_baseline(str(blank_md))
    run.freeze_baseline(str(baseline(tmp_path)))
    assert run.baseline_artifact


def test_exact_version_approval_and_preflight_gates(tmp_path, monkeypatch):
    run = decision()
    run.freeze_baseline(str(baseline(tmp_path)))
    first = run.prepare_action("Founder-reviewed copy", "https://www.ayanabott.com/")
    with pytest.raises(PermissionError):
        run.manual_execution_packet()
    approval, preflight, _, _, evidence = signed_gate(monkeypatch, tmp_path, first)
    with pytest.raises(PermissionError):
        run.record_ceo_approval(Approval("wrong", approval.approved_at, approval.expires_at, approval.signature))
    run.record_ceo_approval(approval)
    with pytest.raises(PermissionError):
        run.manual_execution_packet()
    run.record_preflight(preflight)
    packet = run.manual_execution_packet()
    assert packet["mode"] == "MANUAL_ONLY"
    evidence.write_text('{"changed": true}', encoding='utf-8')
    with pytest.raises(PermissionError):
        run.manual_execution_packet()
    second = run.prepare_action("Changed copy", "https://www.ayanabott.com/")
    assert second.version != first.version
    with pytest.raises(PermissionError):
        run.record_ceo_approval(approval)


def test_no_paid_action_and_outcomes_require_approval(tmp_path, monkeypatch):
    run = decision()
    run.freeze_baseline(str(baseline(tmp_path)))
    with pytest.raises(PermissionError):
        run.prepare_action("Copy", "https://www.ayanabott.com/", maximum_cost_inr=1)
    action = run.prepare_action("Copy", "https://www.ayanabott.com/")
    with pytest.raises(PermissionError):
        run.record_outcome(Outcome(day=1, attributable_visits=0))
    approval, preflight, _, _, _ = signed_gate(monkeypatch, tmp_path, action)
    run.record_ceo_approval(approval)
    with pytest.raises(PermissionError):
        run.record_outcome(Outcome(day=1, attributable_visits=4))
    run.record_preflight(preflight)
    run.manual_execution_packet()
    run.record_outcome(Outcome(day=1, attributable_visits=4, cta_clicks=1, qualified_inquiries=None))
    assert run.outcomes[0].qualified_inquiries is None
    with pytest.raises(ValueError):
        run.record_outcome(Outcome(day=1))
    with pytest.raises(ValueError):
        Outcome(day=2, attributable_visits=1, cta_clicks=2)


def test_local_export_contains_audit_and_no_approval(tmp_path):
    run = decision()
    path = tmp_path / "decision.json"
    run.export_local(str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["approval"] is None
    assert data["audit"][0]["event"] == "decision_generated"


def test_forged_identity_and_caller_flags_cannot_open_gate(tmp_path, monkeypatch):
    run = decision()
    run.freeze_baseline(str(baseline(tmp_path)))
    action = run.prepare_action('Exact copy', 'https://www.ayanabott.com/')
    approval, preflight, _, _, evidence = signed_gate(monkeypatch, tmp_path, action)
    with pytest.raises(TypeError):
        run.manual_execution_packet(production_security_verified=True)
    with pytest.raises(PermissionError):
        run.record_ceo_approval(Approval(action.version, approval.approved_at,
                                         approval.expires_at, base64.b64encode(b'forged').decode()))
    run.record_ceo_approval(approval)
    bad = PreflightAttestation(preflight.version, preflight.observed_at,
                               {**preflight.checks, 'measurement': {'result': 'PASS',
                                'artifact': evidence.name, 'sha256': '0' * 64}}, preflight.signature)
    with pytest.raises(PermissionError):
        run.record_preflight(bad)
    monkeypatch.delenv('FOUNDERREACH_PREFLIGHT_PUBLIC_KEY')
    with pytest.raises(PermissionError):
        run.record_preflight(preflight)
