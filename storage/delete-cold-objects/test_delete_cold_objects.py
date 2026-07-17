"""End-to-end test of delete_cold_objects.py against a mock S3 (moto).

Drives the assembled script through identify -> quarantine -> delete -> recover
-> cleanup exactly as a user would, using the documented CoreWeave 8-column
inventory schema.
"""
import csv
import json
import os
import boto3
from botocore.client import Config
from datetime import datetime, timedelta, timezone
from moto import mock_aws

import delete_cold_objects as dco

os.environ["ACCESS_KEY_ID"] = os.environ["AWS_ACCESS_KEY_ID"] = "testkey"
os.environ["SECRET_ACCESS_KEY"] = os.environ["AWS_SECRET_ACCESS_KEY"] = "testsecret"
os.environ["BUCKET"] = "cold-test"
os.environ["REGION"] = "us-east-1"          # region moto accepts
os.environ.pop("ENDPOINT_URL", None)         # let moto intercept default calls

WORK = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK)
BUCKET = os.environ["BUCKET"]
FIELDS = dco.DEFAULT_FIELDS  # documented 8-column schema

results = []
def check(name, cond, detail=""):
    results.append((name, cond, detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))


def row(key, last_access, is_latest="true", is_dm="false", vid="v1"):
    return {"Bucket": BUCKET, "Key": key, "VersionId": vid, "IsLatest": is_latest,
            "IsDeleteMarker": is_dm, "Size": "10", "StorageClass": "STANDARD",
            "LastAccessedDate": last_access}


def write_inv(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        for r in rows:
            w.writerow([r.get(k, "") for k in FIELDS])


# Point the script's client at moto by overriding endpoint via env each call.
def patched_make_client():
    cfg = Config(region_name="us-east-1", s3={"addressing_style": "virtual"})
    return boto3.client("s3", aws_access_key_id="testkey",
                        aws_secret_access_key="testsecret", config=cfg)


@mock_aws
def run():
    dco.make_client = patched_make_client  # bypass custom endpoint for the mock
    now = datetime.now(timezone.utc)
    old = (now - timedelta(days=200)).strftime("%Y-%m-%dT%H:%M:%SZ")
    recent = (now - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
    accessed_during = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")

    write_inv("inventory.csv", [
        row("cold/1", old), row("cold/2", old), row("cold/3", old),
        row("warm/1", old), row("hot/1", recent), row("noacc", ""),
        row("nc", old, is_latest="false"), row("dm", old, is_dm="true"),
    ])

    s3 = patched_make_client()
    s3.create_bucket(Bucket=BUCKET)
    for k in ["cold/1", "cold/2", "cold/3", "warm/1", "hot/1"]:
        s3.put_object(Bucket=BUCKET, Key=k, Body=b"data")

    # Stage 1
    dco.main(["identify", "--inventory", "inventory.csv", "--threshold-days", "90"])
    state = json.load(open(dco.STATE_FILE))
    check("identify: only cold live objects",
          sorted(state["candidates"]) == ["cold/1", "cold/2", "cold/3", "warm/1"],
          str(sorted(state["candidates"])))

    # Stage 2
    s3.put_object_tagging(Bucket=BUCKET, Key="cold/1",
                          Tagging={"TagSet": [{"Key": "team", "Value": "ml"}]})
    dco.main(["quarantine"])
    tags = {t["Key"]: t["Value"]
            for t in s3.get_object_tagging(Bucket=BUCKET, Key="cold/1")["TagSet"]}
    check("quarantine: tag applied", tags.get("quarantine_set") is not None, str(tags))
    check("quarantine: pre-existing tag preserved", tags.get("team") == "ml", str(tags))
    # backdate quarantine_date to 30 days ago so the buffer window has elapsed
    state = json.load(open(dco.STATE_FILE))
    state["quarantine_date"] = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    json.dump(state, open(dco.STATE_FILE, "w"))

    # Stage 3: fresh inventory — warm/1 accessed during window is spared
    write_inv("inventory_fresh.csv", [
        row("cold/1", old), row("cold/2", old), row("cold/3", old),
        row("warm/1", accessed_during),
    ])
    dco.main(["delete", "--inventory", "inventory_fresh.csv"])
    confirmed = json.load(open(dco.CONFIRMED_FILE))
    check("delete: spares object accessed during window",
          sorted(confirmed) == ["cold/1", "cold/2", "cold/3"], str(sorted(confirmed)))
    check("delete: versioning enabled",
          s3.get_bucket_versioning(Bucket=BUCKET).get("Status") == "Enabled")
    gone = False
    try:
        s3.get_object(Bucket=BUCKET, Key="cold/1")
    except Exception:
        gone = True
    check("delete: object soft-deleted", gone)
    check("delete: warm/1 still live",
          _readable(s3, "warm/1"))

    # Stage 4 recover: restore cold/2
    dco.main(["recover", "cold/2"])
    check("recover: object restored", _readable(s3, "cold/2"))
    confirmed = json.load(open(dco.CONFIRMED_FILE))
    check("recover: key dropped from cleanup list",
          sorted(confirmed) == ["cold/1", "cold/3"], str(sorted(confirmed)))

    # Stage 4 cleanup
    dco.main(["cleanup"])
    lov = s3.list_object_versions(Bucket=BUCKET, Prefix="cold/1")
    remaining = len(lov.get("Versions", [])) + len(lov.get("DeleteMarkers", []))
    check("cleanup: purged key fully removed", remaining == 0, f"remaining={remaining}")
    check("cleanup: restored cold/2 survives", _readable(s3, "cold/2"))
    check("cleanup: unrelated hot/1 survives", _readable(s3, "hot/1"))


def _readable(s3, key):
    try:
        s3.get_object(Bucket=BUCKET, Key=key)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    run()
    passed = sum(1 for _, c, _ in results if c)
    print(f"\n{passed}/{len(results)} checks passed")
    for name, cond, detail in results:
        if not cond:
            print(f"  FAILED: {name} — {detail}")
    raise SystemExit(0 if passed == len(results) else 1)
