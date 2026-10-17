"""Read-only production audit. Prints no credentials or row text.

Run on the owner's machine where Supabase DNS works. Requires .env and psycopg.
This script makes GET/SELECT requests only; it never changes production data.
"""

import json
import os
from pathlib import Path
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
TABLES = ("opportunities", "cost_ledger", "cache", "content_hashes")
FIELDS = ("id", "created_at", "original_url", "discussion_date", "platform",
          "classification", "source_status", "intent_status", "total_score")


def _get(url, key, table, select="*", limit=1000, offset=0):
    params = {"select": select, "limit": limit, "offset": offset}
    if table == "opportunities":
        params["order"] = "id.asc"
    query = urllib.parse.urlencode(params)
    request = urllib.request.Request(
        f"{url.rstrip('/')}/rest/v1/{table}?{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, None


def _public_checks(url, anon):
    secure = True
    for table in TABLES:
        try:
            status, rows = _get(url, anon, table, limit=1)
        except Exception as exc:
            print(f"anon {table}: inconclusive ({type(exc).__name__})")
            secure = False
            continue
        count = len(rows) if rows is not None else "n/a"
        print(f"anon {table}: HTTP {status}; visible_rows={count}")
        if status not in (200, 401, 403) or (status == 200 and rows):
            secure = False
    return secure


def _cloud_rows(url, service):
    all_rows = []
    while True:
        status, rows = _get(url, service, "opportunities", select=",".join(FIELDS), offset=len(all_rows))
        if status != 200 or rows is None:
            raise RuntimeError(f"service read failed with HTTP {status}")
        all_rows.extend(rows)
        if len(rows) < 1000:
            return all_rows


def _service_checks(url, service):
    working = True
    for table in TABLES:
        try:
            status, rows = _get(url, service, table, limit=1)
            print(f"service {table}: HTTP {status}; sample_rows={len(rows) if rows is not None else 'n/a'}")
            if status != 200:
                working = False
        except Exception as exc:
            print(f"service {table}: inconclusive ({type(exc).__name__})")
            working = False
    return working


def _local_rows():
    with sqlite3.connect(ROOT / "data" / "founderreach.db") as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(f"SELECT {','.join(FIELDS)} FROM opportunities")]


def _reconcile(cloud, local):
    cloud_by_id = {row["id"]: row for row in cloud}
    local_by_id = {row["id"]: row for row in local}
    shared = cloud_by_id.keys() & local_by_id.keys()
    compare = tuple(k for k in FIELDS if k not in ("id", "created_at"))
    mismatches = [row_id for row_id in shared
                  if any(str(cloud_by_id[row_id].get(k)) != str(local_by_id[row_id].get(k)) for k in compare)]
    print(f"reconciliation: cloud={len(cloud)} local={len(local)} shared={len(shared)} "
          f"cloud_only={len(cloud_by_id.keys()-local_by_id.keys())} "
          f"local_only={len(local_by_id.keys()-cloud_by_id.keys())} "
          f"shared_field_mismatch_ids={mismatches}")
    for origin, rows, other in (("cloud_only", cloud_by_id, local_by_id),
                                ("local_only", local_by_id, cloud_by_id)):
        for row_id in sorted(rows.keys() - other.keys()):
            row = rows[row_id]
            print(json.dumps({"origin": origin, "id": row_id, "created_at": row.get("created_at"),
                              "original_url": row.get("original_url"),
                              "discussion_date": row.get("discussion_date"),
                              "classification": row.get("classification")}, default=str))
    cloud_only = [cloud_by_id[k] for k in cloud_by_id.keys()-local_by_id.keys()]
    local_only = [local_by_id[k] for k in local_by_id.keys()-cloud_by_id.keys()]
    for left in cloud_only:
        for right in local_only:
            if left.get("original_url") == right.get("original_url"):
                print(f"same_source_url_pair: cloud_id={left['id']} local_id={right['id']}")


def _catalog_readonly(database_url):
    if not database_url:
        print("deployed SQL catalog: DATABASE_URL missing; unverified")
        return False
    try:
        import psycopg
        with psycopg.connect(database_url, connect_timeout=10) as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            names = list(TABLES)
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                           has_table_privilege('anon',c.oid,'SELECT') AS anon_select,
                           has_table_privilege('anon',c.oid,'INSERT') AS anon_insert,
                           has_table_privilege('authenticated',c.oid,'SELECT') AS authenticated_select,
                           has_table_privilege('authenticated',c.oid,'INSERT') AS authenticated_insert,
                           has_table_privilege('authenticated',c.oid,'UPDATE') AS authenticated_update,
                           has_table_privilege('authenticated',c.oid,'DELETE') AS authenticated_delete
                    FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                    WHERE n.nspname='public' AND c.relname=ANY(%s)
                    ORDER BY c.relname
                """, (names,))
                cols = [d.name for d in cursor.description]
                grants = [dict(zip(cols, row)) for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT tablename, policyname, roles::text, cmd, qual, with_check
                    FROM pg_policies WHERE schemaname='public' AND tablename=ANY(%s)
                    ORDER BY tablename,policyname
                """, (names,))
                cols = [d.name for d in cursor.description]
                policies = [dict(zip(cols, row)) for row in cursor.fetchall()]
            print("deployed_table_access=" + json.dumps(grants, default=str))
            print("deployed_policies=" + json.dumps(policies, default=str))
            if len(grants) != len(TABLES):
                print("CATALOG INCOMPLETE: expected four tables")
                return False
            broader = [g["relname"] for g in grants if any(g[k] for k in
                       ("authenticated_select", "authenticated_insert", "authenticated_update", "authenticated_delete"))]
            print("authenticated_grants_present=" + json.dumps(broader))
            return True
    except Exception as exc:
        print(f"deployed SQL catalog: unverified ({type(exc).__name__})")
        return False


def main():
    url = os.getenv("SUPABASE_URL", "")
    anon = os.getenv("SUPABASE_ANON_KEY", "")
    service = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
    if not url.startswith("https://") or not anon or not service:
        print("Missing URL or read credentials; no audit possible")
        return 2
    anon_ok = _public_checks(url, anon)
    service_ok = _service_checks(url, service)
    try:
        cloud = _cloud_rows(url, service)
        print(f"service opportunities: HTTP 200; rows={len(cloud)}")
        _reconcile(cloud, _local_rows())
    except Exception as exc:
        print(f"service/reconciliation: unverified ({type(exc).__name__})")
        service_ok = False
    catalog_ok = _catalog_readonly(os.getenv("DATABASE_URL", ""))
    return 0 if anon_ok and service_ok and catalog_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
