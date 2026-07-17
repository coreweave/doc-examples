#!/usr/bin/env python3
"""Delete cold objects from CoreWeave AI Object Storage.

A safe, staged workflow for identifying and deleting cold objects when the
source of truth for the data lives elsewhere. See the companion guide:
https://docs.coreweave.com/products/storage/object-storage/using-object-storage/delete-cold-objects

The workflow runs in four stages, each a subcommand:

  identify   Stage 1  Read an inventory report and list cold candidates.
  quarantine Stage 2  Tag candidates and persist state for the buffer window.
  delete     Stage 3  Re-check access times, enable versioning, delete cold keys.
  cleanup    Stage 4  Permanently remove recovery copies and delete markers.

Plus a recovery helper for undoing mistakes before cleanup runs:

  recover    Stage 4  Restore mistakenly deleted keys by removing delete markers.

Stages 1 and 2 typically run together; stages 3 and 4 run later, in separate
processes, after the buffer and recovery windows elapse. State is passed
between stages through two local JSON files.

Configuration comes from environment variables:

  export ACCESS_KEY_ID="[ACCESS-KEY-ID]"
  export SECRET_ACCESS_KEY="[SECRET-ACCESS-KEY]"
  export BUCKET="[BUCKET-NAME]"
  # Optional, with defaults shown:
  export ENDPOINT_URL="https://cwobject.com"   # LOTA: http://cwlota.com
  export REGION="US-EAST-04A"

Example:

  python delete_cold_objects.py identify --inventory inventory.csv --threshold-days 90
  python delete_cold_objects.py quarantine
  # ...wait the buffer window (for example, 30 days)...
  python delete_cold_objects.py delete --inventory inventory_fresh.csv
  # ...wait the recovery window (for example, 30 days)...
  python delete_cold_objects.py cleanup
"""

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import boto3
from botocore.client import Config

# Column order is set by your inventory configuration and listed in the
# report's manifest.json (fileSchema). This default matches the schema shown in
# the CoreWeave Inventory Reporting docs. Verify it against your own
# manifest.json before relying on the output; a mismatch silently misaligns
# every column because the CSV is headerless.
DEFAULT_FIELDS = [
    "Bucket", "Key", "VersionId", "IsLatest", "IsDeleteMarker",
    "Size", "StorageClass", "LastAccessedDate",
]

QUARANTINE_TAG_KEY = "quarantine_set"
STATE_FILE = "quarantine_state.json"
CONFIRMED_FILE = "confirmed_candidates.json"


# --------------------------------------------------------------------------- #
# Client and helpers
# --------------------------------------------------------------------------- #
def make_client():
    """Build an S3 client for AI Object Storage from environment variables."""
    boto_config = Config(
        region_name=os.environ.get("REGION", "US-EAST-04A"),
        s3={"addressing_style": "virtual"},
    )
    return boto3.client(
        "s3",
        endpoint_url=os.environ.get("ENDPOINT_URL", "https://cwobject.com"),
        aws_access_key_id=os.environ["ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["SECRET_ACCESS_KEY"],
        config=boto_config,
    )


def require_bucket():
    bucket = os.environ.get("BUCKET")
    if not bucket:
        sys.exit("Set the BUCKET environment variable to the source bucket name.")
    return bucket


def parse_last_access(value):
    """Parse an RFC 3339 timestamp. The 'Z' -> '+00:00' swap keeps this working
    on Python versions before 3.11."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def read_candidates(inventory_path, fields, keep=None):
    """Yield keys of current live objects that have a LastAccessedDate.

    keep, if given, is a predicate on the parsed last-access datetime.
    """
    with open(inventory_path) as f:
        # Inventory CSVs are headerless; provide column names explicitly.
        reader = csv.DictReader(f, fieldnames=fields)
        for row in reader:
            # Only consider current live objects.
            if row["IsLatest"] != "true" or row["IsDeleteMarker"] == "true":
                continue
            if not row["LastAccessedDate"]:
                continue
            last_access = parse_last_access(row["LastAccessedDate"])
            if keep is None or keep(last_access):
                yield row["Key"], last_access


# --------------------------------------------------------------------------- #
# Stage 1: Identify
# --------------------------------------------------------------------------- #
def cmd_identify(args):
    fields = args.fields.split(",") if args.fields else DEFAULT_FIELDS
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.threshold_days)

    candidates = [
        key for key, _ in read_candidates(
            args.inventory, fields, keep=lambda last: last < cutoff
        )
    ]
    with open(STATE_FILE, "w") as f:
        json.dump({"quarantine_date": None, "candidates": candidates}, f)
    print(f"Identified {len(candidates)} cold candidate(s); wrote {STATE_FILE}.")


# --------------------------------------------------------------------------- #
# Stage 2: Quarantine
# --------------------------------------------------------------------------- #
def cmd_quarantine(args):
    s3 = make_client()
    bucket = require_bucket()

    with open(STATE_FILE) as f:
        state = json.load(f)
    candidates = state["candidates"]

    quarantine_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    quarantine_tag = {"Key": QUARANTINE_TAG_KEY, "Value": quarantine_date}

    for key in candidates:
        # Fetch existing tags so you don't overwrite them.
        response = s3.get_object_tagging(Bucket=bucket, Key=key)
        existing_tags = response.get("TagSet", [])
        # Drop any prior quarantine_set tag, then append the current one so the
        # workflow is safe to re-run.
        merged_tags = [t for t in existing_tags if t["Key"] != QUARANTINE_TAG_KEY]
        merged_tags.append(quarantine_tag)
        s3.put_object_tagging(Bucket=bucket, Key=key, Tagging={"TagSet": merged_tags})

    state["quarantine_date"] = quarantine_date
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
    print(f"Quarantined {len(candidates)} object(s) with {QUARANTINE_TAG_KEY}="
          f"{quarantine_date}; updated {STATE_FILE}.")


# --------------------------------------------------------------------------- #
# Stage 3: Delete
# --------------------------------------------------------------------------- #
def cmd_delete(args):
    s3 = make_client()
    bucket = require_bucket()
    fields = args.fields.split(",") if args.fields else DEFAULT_FIELDS

    with open(STATE_FILE) as f:
        state = json.load(f)
    quarantine_date = state["quarantine_date"]
    candidates = state["candidates"]
    if not quarantine_date:
        sys.exit("State has no quarantine_date; run the quarantine stage first.")

    quarantine_start = datetime.strptime(quarantine_date, "%Y-%m-%d").replace(
        tzinfo=timezone.utc
    )
    quarantined_keys = set(candidates)

    # Re-check a fresh inventory generated AFTER the buffer window closed. Keys
    # accessed during the window have a newer LastAccessedDate and are spared.
    confirmed_candidates = [
        key for key, last in read_candidates(
            args.inventory, fields, keep=lambda last: last < quarantine_start
        )
        if key in quarantined_keys
    ]

    # Ensure versioning is on so each delete is recoverable. Idempotent.
    s3.put_bucket_versioning(
        Bucket=bucket, VersioningConfiguration={"Status": "Enabled"}
    )

    # delete_objects accepts up to 1000 keys per call and returns HTTP 200 even
    # when individual keys fail, so inspect the Errors list in each response.
    errors = []
    for i in range(0, len(confirmed_candidates), 1000):
        batch = [{"Key": k} for k in confirmed_candidates[i:i + 1000]]
        resp = s3.delete_objects(Bucket=bucket, Delete={"Objects": batch})
        errors.extend(resp.get("Errors", []))

    with open(CONFIRMED_FILE, "w") as f:
        json.dump(confirmed_candidates, f)

    print(f"Deleted {len(confirmed_candidates)} confirmed cold key(s); "
          f"wrote {CONFIRMED_FILE}.")
    if errors:
        print(f"{len(errors)} delete(s) failed; first error: {errors[0]}")


# --------------------------------------------------------------------------- #
# Stage 4: Recover (optional, before cleanup)
# --------------------------------------------------------------------------- #
def cmd_recover(args):
    s3 = make_client()
    bucket = require_bucket()
    keys_to_recover = set(args.keys)

    # Remove the current delete marker for each key, promoting its recovery copy
    # back to current. Recover the whole set in one pass, then filter the state
    # file once, so concurrent single-key runs can't clobber each other.
    paginator = s3.get_paginator("list_object_versions")
    markers_to_remove = []
    for page in paginator.paginate(Bucket=bucket):
        for marker in page.get("DeleteMarkers", []):
            if marker["Key"] in keys_to_recover and marker["IsLatest"]:
                markers_to_remove.append(
                    {"Key": marker["Key"], "VersionId": marker["VersionId"]}
                )

    errors = []
    for i in range(0, len(markers_to_remove), 1000):
        resp = s3.delete_objects(
            Bucket=bucket, Delete={"Objects": markers_to_remove[i:i + 1000]}
        )
        errors.extend(resp.get("Errors", []))

    failed_keys = {e["Key"] for e in errors}
    recovered = keys_to_recover - failed_keys

    # Drop only successfully recovered keys from the cleanup list so a key whose
    # marker removal failed stays in the list and is retried or cleaned up.
    try:
        with open(CONFIRMED_FILE) as f:
            confirmed = json.load(f)
        confirmed = [k for k in confirmed if k not in recovered]
        with open(CONFIRMED_FILE, "w") as f:
            json.dump(confirmed, f)
    except FileNotFoundError:
        pass

    print(f"Recovered {len(recovered)} key(s).")
    if failed_keys:
        print(f"{len(failed_keys)} key(s) could not be recovered; "
              f"first error: {errors[0]}")


# --------------------------------------------------------------------------- #
# Stage 4: Cleanup
# --------------------------------------------------------------------------- #
def cmd_cleanup(args):
    s3 = make_client()
    bucket = require_bucket()

    with open(CONFIRMED_FILE) as f:
        confirmed_candidates = set(json.load(f))

    paginator = s3.get_paginator("list_object_versions")
    versions_by_key = defaultdict(list)
    current_is_delete_marker = {}

    # A full-bucket listing is simplest. If confirmed_candidates is small
    # relative to the bucket, list per key with Prefix=key instead.
    for page in paginator.paginate(Bucket=bucket):
        for v in page.get("Versions", []):
            if v["Key"] in confirmed_candidates:
                versions_by_key[v["Key"]].append(
                    {"Key": v["Key"], "VersionId": v["VersionId"]}
                )
                if v["IsLatest"]:
                    current_is_delete_marker[v["Key"]] = False
        for m in page.get("DeleteMarkers", []):
            if m["Key"] in confirmed_candidates:
                versions_by_key[m["Key"]].append(
                    {"Key": m["Key"], "VersionId": m["VersionId"]}
                )
                if m["IsLatest"]:
                    current_is_delete_marker[m["Key"]] = True

    # Purge only keys whose current version is still a delete marker. A key that
    # was restored or re-created since Stage 3 has a live current version and is
    # left untouched.
    to_delete = []
    skipped = []
    for key in confirmed_candidates:
        if current_is_delete_marker.get(key) is True:
            to_delete.extend(versions_by_key[key])
        else:
            skipped.append(key)

    errors = []
    for i in range(0, len(to_delete), 1000):
        resp = s3.delete_objects(
            Bucket=bucket, Delete={"Objects": to_delete[i:i + 1000]}
        )
        errors.extend(resp.get("Errors", []))

    print(f"Purged versions for {len(confirmed_candidates) - len(skipped)} key(s).")
    if errors:
        print(f"{len(errors)} version(s) failed to delete; first error: {errors[0]}")
    if skipped:
        print(f"Skipped {len(skipped)} key(s) no longer in a deleted state.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser():
    parser = argparse.ArgumentParser(
        description="Safely identify and delete cold objects in CoreWeave AI "
                    "Object Storage.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_identify = sub.add_parser("identify", help="Stage 1: list cold candidates.")
    p_identify.add_argument("--inventory", default="inventory.csv",
                            help="Local inventory CSV path (default: inventory.csv).")
    p_identify.add_argument("--threshold-days", type=int, default=90,
                            help="Cold threshold in days (default: 90).")
    p_identify.add_argument("--fields", default="",
                            help="Comma-separated inventory column names. "
                                 "Defaults to the documented CoreWeave schema.")
    p_identify.set_defaults(func=cmd_identify)

    p_quar = sub.add_parser("quarantine", help="Stage 2: tag candidates, save state.")
    p_quar.set_defaults(func=cmd_quarantine)

    p_del = sub.add_parser("delete", help="Stage 3: re-check, version, delete.")
    p_del.add_argument("--inventory", default="inventory_fresh.csv",
                       help="Fresh inventory CSV generated after the buffer "
                            "window (default: inventory_fresh.csv).")
    p_del.add_argument("--fields", default="",
                       help="Comma-separated inventory column names.")
    p_del.set_defaults(func=cmd_delete)

    p_rec = sub.add_parser("recover", help="Stage 4: restore mistakenly deleted keys.")
    p_rec.add_argument("keys", nargs="+", help="Object keys to restore.")
    p_rec.set_defaults(func=cmd_recover)

    p_clean = sub.add_parser("cleanup", help="Stage 4: permanently remove copies.")
    p_clean.set_defaults(func=cmd_cleanup)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
