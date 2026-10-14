# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

mock_provider "coreweave" {}

run "single_zone" {
  command = plan
  variables {
    inventory_by_zone = {
      "US-EAST-04A" = {
        source_buckets     = ["east-source"]
        destination_bucket = "east-reports"
      }
    }
  }
  assert {
    condition     = length(output.inventory_configurations) == 1 && output.inventory_configurations["US-EAST-04A"]["east-source"].destination_bucket == "east-reports"
    error_message = "A single-zone configuration must route its source to its destination."
  }
}

run "multiple_zones" {
  command = plan
  variables {
    inventory_by_zone = {
      "US-EAST-04A" = {
        source_buckets     = ["east-source", "east-checkpoints"]
        destination_bucket = "east-reports"
      }
      "US-WEST-09A" = {
        source_buckets            = ["west-source"]
        destination_bucket        = "west-reports"
        create_destination_bucket = true
      }
    }
    report_format = "Parquet"
    enabled       = false
  }
  assert {
    condition     = length(output.inventory_configurations) == 2 && length(output.inventory_configurations["US-EAST-04A"]) == 2 && length(output.inventory_configurations["US-WEST-09A"]) == 1
    error_message = "Preserve all source buckets within their zone."
  }
  assert {
    condition = alltrue(flatten([
      for zone, configurations in output.inventory_configurations : [
        for configuration in values(configurations) : configuration.destination_bucket == (zone == "US-EAST-04A" ? "east-reports" : "west-reports") && configuration.format == "Parquet" && configuration.enabled == false
      ]
    ]))
    error_message = "Route each zone to its own destination and propagate shared report settings."
  }
}

run "reject_duplicate_source" {
  command = plan
  variables {
    inventory_by_zone = {
      "US-EAST-04A" = {
        source_buckets     = ["same-source"]
        destination_bucket = "east-reports"
      }
      "US-WEST-09A" = {
        source_buckets     = ["same-source"]
        destination_bucket = "west-reports"
      }
    }
  }
  expect_failures = [var.inventory_by_zone]
}

run "reject_shared_destination" {
  command = plan
  variables {
    inventory_by_zone = {
      "US-EAST-04A" = {
        source_buckets     = ["east-source"]
        destination_bucket = "same-reports"
      }
      "US-WEST-09A" = {
        source_buckets     = ["west-source"]
        destination_bucket = "same-reports"
      }
    }
  }
  expect_failures = [var.inventory_by_zone]
}

run "reject_empty_zones" {
  command = plan
  variables {
    inventory_by_zone = {}
  }
  expect_failures = [var.inventory_by_zone]
}
