"""Read-only cloud/local preflight. Never prints keys, row content, or PII."""

import json
import os
from pathlib import Path
import socket
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
TABLES = ("opportunities", "cost_ledger", "cache", "content_hashes")
COMPARE = ("id", "classification", "source_status", "intent_status", "total_score", "discussion_date", "original_url")


def fetch(url: str, key: str, table: str, select: str = "*", limit: int = 1):
    query = urllib.parse.urlencode({"select": select, "limit": str(limit)})
    request = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/{table}?{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status, json.load(response), None
    except urllib.error.HTTPError as exc:
        return exc.code, None, "HTTP error"
    except Exception as exc:
        return None, None, type(exc).__name__


def main():
    url = os.getenv("SUPABASE_URL", "")
    host = urllib.parse.urlparse(url).hostname
    if not host:
        print("Supabase URL missing")
        return 2
    try:
        socket.getaddrinfo(host, 443)
        print("DNS: resolved")
    except OSError as exc:
        print(f"DNS: unavailable ({type(exc).__name__}); no deployed security claim possible")
        return 2

    anon = os.getenv("SUPABASE_ANON_KEY", "")
    service = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not anon or not service:
        print("Required read credentials missing; no live audit possible")
        return 2
    for table in TABLES:
        status, rows, error = fetch(url, anon, table)
        print(f"anon {table}: status={status} rows={len(rows) if rows is not None else 'n/a'} error={error}")
        if status == 200 and rows:
            print("SECURITY FAIL: anonymous reader received protected rows")
            return 1
        if status not in (200, 401, 403):
            print("Anonymous result inconclusive; stop before reconciliation approval")
            return 2

    status, cloud, error = fetch(url, service, "opportunities", select=",".join(COMPARE), limit=1000)
    print(f"service opportunities: status={status} rows={len(cloud) if cloud is not None else 'n/a'} error={error}")
    if status != 200 or cloud is None:
        return 2
    with sqlite3.connect(ROOT / "data" / "founderreach.db") as conn:
        conn.row_factory = sqlite3.Row
        local = [dict(r) for r in conn.execute(f"SELECT {','.join(COMPARE)} FROM opportunities")]
    cloud_by_id = {r["id"]: r for r in cloud}
    local_by_id = {r["id"]: r for r in local}
    shared = cloud_by_id.keys() & local_by_id.keys()
    mismatches = sum(any(str(cloud_by_id[i].get(k)) != str(local_by_id[i].get(k)) for k in COMPARE) for i in shared)
    print(f"reconciliation: cloud={len(cloud)} local={len(local)} shared={len(shared)} "
          f"cloud_only={len(cloud_by_id.keys()-local_by_id.keys())} "
          f"local_only={len(local_by_id.keys()-cloud_by_id.keys())} field_mismatches={mismatches}")
    print("Policy definitions/grants still require a privileged read-only SQL inspection")
    return 0 if not mismatches and len(cloud_by_id) == len(local_by_id) else 1


if __name__ == "__main__":
    raise SystemExit(main())
