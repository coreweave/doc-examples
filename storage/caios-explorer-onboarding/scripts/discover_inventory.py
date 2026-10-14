#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

"""Build Terraform JSON variables using read-only Boto3 bucket discovery."""

import argparse
from contextlib import closing
import fnmatch
import json
from pathlib import Path
import re
import sys

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError


class DiscoveryError(Exception):
    pass


def create_client(args):
    session = boto3.Session(profile_name=args.profile)
    return session.client(
        "s3",
        endpoint_url=args.endpoint_url,
        config=Config(
            s3={"addressing_style": "virtual"},
            connect_timeout=10,
            read_timeout=30,
            retries={"mode": "standard", "total_max_attempts": 3},
        ),
    )


def list_bucket_names(client):
    names = set()
    try:
        for response in client.get_paginator("list_buckets").paginate():
            buckets = response.get("Buckets")
            if not isinstance(buckets, list) or any(
                not isinstance(b, dict) or not isinstance(b.get("Name"), str) for b in buckets
            ):
                raise DiscoveryError("ListBuckets: expected a Buckets array with names")
            names.update(b["Name"] for b in buckets)
    except (BotoCoreError, ClientError) as exc:
        raise DiscoveryError(f"ListBuckets: {exc}") from exc
    return names


def zone_for(client, bucket):
    # Botocore forces GetBucketLocation to path style, which CAIOS rejects.
    try:
        zone = client.head_bucket(Bucket=bucket).get("BucketRegion")
    except (BotoCoreError, ClientError) as exc:
        raise DiscoveryError(f"HeadBucket {bucket}: {exc}") from exc
    if not isinstance(zone, str) or not re.fullmatch(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+", zone):
        raise DiscoveryError(f"{bucket}: missing or unsupported CAIOS zone format: {zone!r}")
    return zone.upper()


def discover(args, client):
    names = list_bucket_names(client)
    selected = sorted(
        name for name in names
        if (not args.include or any(fnmatch.fnmatchcase(name, p) for p in args.include))
        and not any(fnmatch.fnmatchcase(name, p) for p in args.exclude)
    )
    if not selected:
        raise DiscoveryError("No source buckets matched the selection")
    locations = {}
    failures = {}
    for name in selected:
        try:
            locations[name] = zone_for(client, name)
        except DiscoveryError as exc:
            failures[name] = str(exc).removeprefix(f"{name}: ")

    grouped = {}
    requested_zones = set(args.zone)
    discovered_zones = set(locations.values())
    zones = discovered_zones & requested_zones if requested_zones else discovered_zones
    for zone in sorted(zones):
        destination = f"{args.destination_prefix}-{zone.lower()}"
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", destination) or destination.startswith(("cw-")):
            raise DiscoveryError(f"Invalid generated destination name: {destination}")
        sources = sorted(name for name, actual_zone in locations.items() if actual_zone == zone and name != destination)
        existing = destination in names
        if existing:
            try:
                if destination in failures:
                    raise DiscoveryError(failures[destination])
                destination_zone = locations.get(destination) or zone_for(client, destination)
                if destination_zone != zone:
                    raise DiscoveryError(f"zone {destination_zone} does not match {zone}")
            except DiscoveryError as exc:
                failures[destination] = str(exc)
                for name in sources:
                    failures[name] = f"destination {destination} could not be verified: {exc}"
                continue
        if sources:
            grouped[zone] = {
                "source_buckets": sources,
                "destination_bucket": destination,
                "create_destination_bucket": not existing,
            }
    if failures:
        print(f"Skipped {len(failures)} bucket(s):", file=sys.stderr)
        for name, reason in sorted(failures.items()):
            print(f"  {name}: {reason}", file=sys.stderr)
    missing_zones = requested_zones - set(grouped)
    if missing_zones:
        print(f"No usable source buckets for requested zone(s): {', '.join(sorted(missing_zones))}", file=sys.stderr)
    if not grouped:
        raise DiscoveryError("No usable source buckets remain after discovery")
    return {"inventory_by_zone": grouped}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", help="Shared AWS profile; otherwise use the Boto3 default credential chain")
    parser.add_argument("--endpoint-url", help="Override the S3 endpoint from the shared profile or environment")
    parser.add_argument("--destination-prefix", required=True, help="Destination names become PREFIX-<zone in lowercase>")
    parser.add_argument("--zone", action="append", default=[], type=str.upper, metavar="ZONE", help="Include sources in this zone; repeat for multiple zones. Defaults to all zones")
    parser.add_argument("--include", action="append", default=[], metavar="GLOB", help="Include matching source names; repeatable, defaults to all buckets")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB", help="Exclude matching source names before location lookups; repeatable")
    parser.add_argument("--output", type=Path, help="Write a new .tfvars.json file; refuses to overwrite. Defaults to stdout")
    args = parser.parse_args(argv)
    try:
        if args.output and args.output.exists():
            raise DiscoveryError(f"Output already exists: {args.output}")
        with closing(create_client(args)) as client:
            payload = json.dumps(discover(args, client), indent=2) + "\n"
        if args.output:
            with args.output.open("x") as output:
                output.write(payload)
        else:
            sys.stdout.write(payload)
    except (DiscoveryError, OSError, BotoCoreError, ClientError) as exc:
        print(f"Discovery failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
