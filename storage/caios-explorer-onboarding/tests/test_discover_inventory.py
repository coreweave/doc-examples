# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

import argparse
from contextlib import closing
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import boto3
from botocore.config import Config
from botocore.stub import Stubber

spec = importlib.util.spec_from_file_location("discover", Path(__file__).parents[1] / "scripts/discover_inventory.py")
discover = importlib.util.module_from_spec(spec)
spec.loader.exec_module(discover)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.client = boto3.client(
            "s3", region_name="us-east-1", endpoint_url="https://cwobject.com",
            aws_access_key_id="test", aws_secret_access_key="test",
            config=Config(s3={"addressing_style": "virtual"}),
        )
        self.stub = Stubber(self.client)
        self.stub.activate()
        self.addCleanup(self.stub.deactivate)
        self.addCleanup(self.client.close)

    def args(self, **changes):
        values = dict(profile="example-profile", endpoint_url=None, destination_prefix="reports", include=[], exclude=[], zone=[])
        return argparse.Namespace(**(values | changes))

    def buckets(self, names, **extra):
        self.stub.add_response("list_buckets", {"Buckets": [{"Name": name} for name in names], **extra}, {})

    def location(self, name, zone):
        self.stub.add_response("head_bucket", {} if zone is None else {"BucketRegion": zone}, {"Bucket": name})

    def run_main(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(discover, "create_client", return_value=self.client), patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            code = discover.main(["--destination-prefix", "reports", *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_pagination_groups_zones_and_reuses_destination(self):
        self.buckets(["east", "reports-us-east-04a"], ContinuationToken="next")
        self.stub.add_response("list_buckets", {"Buckets": [{"Name": "west"}]}, {"ContinuationToken": "next"})
        self.location("east", "us-east-04a")
        self.location("reports-us-east-04a", "US-EAST-04A")
        self.location("west", "US-WEST-09A")
        result = discover.discover(self.args(), self.client)["inventory_by_zone"]
        self.assertEqual(result["US-EAST-04A"]["source_buckets"], ["east"])
        self.assertFalse(result["US-EAST-04A"]["create_destination_bucket"])
        self.assertTrue(result["US-WEST-09A"]["create_destination_bucket"])
        self.stub.assert_no_pending_responses()

    def test_single_zone_is_case_insensitive(self):
        self.buckets(["east", "west"])
        self.location("east", "US-EAST-04A")
        self.location("west", "US-WEST-09A")
        code, stdout, stderr = self.run_main("--zone", "us-east-04a")
        self.assertEqual(code, 0)
        self.assertEqual(list(json.loads(stdout)["inventory_by_zone"]), ["US-EAST-04A"])
        self.assertEqual(stderr, "")

    def test_multiple_zone_filter(self):
        self.buckets(["east", "other", "west"])
        self.location("east", "US-EAST-04A")
        self.location("other", "US-EAST-02A")
        self.location("west", "US-WEST-09A")
        code, stdout, _ = self.run_main("--zone", "US-EAST-04A", "--zone", "US-WEST-09A")
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(stdout)["inventory_by_zone"]), {"US-EAST-04A", "US-WEST-09A"})

    def test_name_filters_before_location_lookup(self):
        self.buckets(["data-a", "data-backup", "private"])
        self.location("data-a", "US-EAST-04A")
        result = discover.discover(self.args(include=["data-*"], exclude=["*-backup"]), self.client)
        self.assertEqual(result["inventory_by_zone"]["US-EAST-04A"]["source_buckets"], ["data-a"])
        self.stub.assert_no_pending_responses()

    def test_partial_failure_keeps_valid_json(self):
        self.buckets(["denied", "good", "legacy", "missing"])
        self.stub.add_client_error("head_bucket", "AccessDenied", expected_params={"Bucket": "denied"})
        self.location("good", "US-EAST-04A")
        self.location("legacy", "RNO2A")
        self.location("missing", None)
        code, stdout, stderr = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)["inventory_by_zone"]["US-EAST-04A"]["source_buckets"], ["good"])
        for detail in ["Skipped 3", "denied", "AccessDenied", "legacy", "RNO2A", "missing"]:
            self.assertIn(detail, stderr)

    def test_destination_failure_skips_only_affected_zone(self):
        self.buckets(["east", "west", "reports-us-east-04a"])
        self.location("east", "US-EAST-04A")
        self.location("west", "US-WEST-09A")
        self.location("reports-us-east-04a", "US-WEST-09A")
        code, stdout, stderr = self.run_main("--include", "east", "--include", "west")
        self.assertEqual(code, 0)
        self.assertEqual(list(json.loads(stdout)["inventory_by_zone"]), ["US-WEST-09A"])
        self.assertIn("east: destination reports-us-east-04a", stderr)

    def test_all_failed_leaves_no_output(self):
        self.buckets(["legacy"])
        self.location("legacy", "RNO2A")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "inventory.tfvars.json"
            code, stdout, stderr = self.run_main("--output", str(output))
            self.assertEqual(code, 1)
            self.assertFalse(output.exists())
            self.assertEqual(stdout, "")
            self.assertIn("legacy", stderr)

    def test_no_zone_match_leaves_no_output(self):
        self.buckets(["east"])
        self.location("east", "US-EAST-04A")
        code, stdout, stderr = self.run_main("--zone", "US-WEST-09A")
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("No usable source buckets for requested zone(s): US-WEST-09A", stderr)

    def test_list_failure_is_fatal(self):
        self.stub.add_client_error("list_buckets", "AccessDenied", expected_params={})
        code, stdout, stderr = self.run_main()
        self.assertEqual(code, 1)
        self.assertEqual(stdout, "")
        self.assertIn("ListBuckets", stderr)

    def test_writes_file_and_refuses_overwrite(self):
        self.buckets(["east"])
        self.location("east", "US-EAST-04A")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "inventory.tfvars.json"
            self.assertEqual(self.run_main("--output", str(output))[0], 0)
            original = output.read_text()
            self.assertIn("US-EAST-04A", json.loads(original)["inventory_by_zone"])
            self.assertEqual(self.run_main("--output", str(output))[0], 1)
            self.assertEqual(output.read_text(), original)

    def test_sdk_profile_endpoint_and_virtual_host_override(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "config"
            original = "[profile example-profile]\nregion = us-east-1\nendpoint_url = https://cwobject.com\ns3 =\n    addressing_style = path\n"
            config.write_text(original)
            credentials = Path(directory) / "credentials"
            credentials.write_text("[example-profile]\naws_access_key_id = test\naws_secret_access_key = test\n")
            with patch.dict(os.environ, {"AWS_CONFIG_FILE": str(config), "AWS_SHARED_CREDENTIALS_FILE": str(credentials)}):
                with closing(discover.create_client(self.args())) as client:
                    self.assertEqual(client.meta.endpoint_url, "https://cwobject.com")
                    self.assertEqual(client.meta.config.s3["addressing_style"], "virtual")
                with closing(discover.create_client(self.args(endpoint_url="https://example.com"))) as client:
                    self.assertEqual(client.meta.endpoint_url, "https://example.com")
            self.assertEqual(config.read_text(), original)


if __name__ == "__main__":
    unittest.main()
