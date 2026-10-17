"""Local, fail-closed approval verification. No action execution capability.

CEO and preflight public keys are pinned by the operator's environment. The
request cannot choose either identity. Private keys never enter this service.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


ROOT = Path(__file__).resolve().parents[1]
CHECKS = frozenset({'production_security', 'measurement', 'channel_permission'})


@dataclass(frozen=True)
class Approval:
    version: str
    approved_at: str
    expires_at: str
    signature: str


@dataclass(frozen=True)
class PreflightAttestation:
    version: str
    observed_at: str
    checks: dict
    signature: str


def _time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (TypeError, ValueError) as exc:
        raise PermissionError('Invalid approval or preflight timestamp') from exc
    if parsed.tzinfo is None:
        raise PermissionError('Timestamp must include timezone')
    return parsed.astimezone(timezone.utc)


def _key(env_name: str) -> bytes:
    encoded = os.environ.get(env_name, '')
    try:
        raw = base64.b64decode(encoded, validate=True)
        if len(raw) != 32:
            raise ValueError('wrong key length')
        return raw
    except (ValueError, TypeError) as exc:
        raise PermissionError(f'{env_name} must contain a pinned Ed25519 public key') from exc


def _verify(key: bytes, signature: str, message: bytes) -> None:
    try:
        Ed25519PublicKey.from_public_bytes(key).verify(base64.b64decode(signature, validate=True), message)
    except (InvalidSignature, ValueError, TypeError) as exc:
        raise PermissionError('Invalid signed authorization evidence') from exc


def action_digest(action) -> str:
    payload = {key: getattr(action, key) for key in
               ('experiment_rank', 'exact_copy', 'destination', 'channel', 'maximum_cost_inr')}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def approval_message(approval: Approval) -> bytes:
    payload = {'purpose': 'founderreach.ceo-approval.v1', 'version': approval.version,
               'approved_at': approval.approved_at, 'expires_at': approval.expires_at}
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def preflight_message(attestation: PreflightAttestation) -> bytes:
    payload = {'purpose': 'founderreach.preflight.v1', 'version': attestation.version,
               'observed_at': attestation.observed_at, 'checks': attestation.checks}
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()


def verify_approval(action, approval: Approval) -> str:
    if action_digest(action) != action.version or approval.version != action.version:
        raise PermissionError('CEO signature does not match the exact action digest')
    now = datetime.now(timezone.utc)
    approved_at, expires_at = _time(approval.approved_at), _time(approval.expires_at)
    if approved_at > now + timedelta(minutes=5) or expires_at <= now or expires_at - approved_at > timedelta(days=7):
        raise PermissionError('CEO approval is expired or outside the allowed window')
    key = _key('FOUNDERREACH_CEO_PUBLIC_KEY')
    _verify(key, approval.signature, approval_message(approval))
    return hashlib.sha256(key).hexdigest()[:16]


def verify_preflight(action, attestation: PreflightAttestation) -> str:
    if action_digest(action) != action.version or attestation.version != action.version:
        raise PermissionError('Preflight does not match the exact action digest')
    observed = _time(attestation.observed_at)
    now = datetime.now(timezone.utc)
    if observed > now + timedelta(minutes=5) or now - observed > timedelta(hours=24):
        raise PermissionError('Preflight evidence is stale or from the future')
    if set(attestation.checks) != CHECKS:
        raise PermissionError('All required preflight checks must be independently evidenced')
    for name, item in attestation.checks.items():
        if not isinstance(item, dict) or set(item) != {'result', 'artifact', 'sha256'} or item['result'] != 'PASS':
            raise PermissionError(f'{name} has no passing evidence')
        path = (ROOT / item['artifact']).resolve()
        try:
            path.relative_to(ROOT)
        except ValueError as exc:
            raise PermissionError('Preflight artifact must be inside the project') from exc
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise PermissionError(f'{name} evidence artifact changed or is missing')
    ceo_key = _key('FOUNDERREACH_CEO_PUBLIC_KEY')
    verifier_key = _key('FOUNDERREACH_PREFLIGHT_PUBLIC_KEY')
    if ceo_key == verifier_key:
        raise PermissionError('Preflight must have a separate verifier identity')
    _verify(verifier_key, attestation.signature, preflight_message(attestation))
    return hashlib.sha256(verifier_key).hexdigest()[:16]
