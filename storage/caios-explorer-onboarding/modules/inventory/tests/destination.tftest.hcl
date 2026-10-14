# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

mock_provider "coreweave" {
  mock_data "coreweave_caller_identity" {
    defaults = {
      organization_id = "example-org"
      principal_id    = "example-user"
    }
  }
}

variables {
  source_buckets     = ["example-source"]
  destination_bucket = "example-reports"
  destination_zone   = "US-EAST-04A"
}

run "existing_destination" {
  command = plan

  assert {
    condition     = length(coreweave_object_storage_bucket.destination) == 0 && length(coreweave_object_storage_bucket_policy.destination) == 0 && length(data.coreweave_caller_identity.current) == 0
    error_message = "Existing destinations must retain their independent bucket and policy management."
  }
  assert {
    condition     = coreweave_object_storage_bucket_inventory.catalog["example-source"].destination.bucket.bucket_arn == "arn:aws:s3:::example-reports"
    error_message = "Inventory must use the supplied destination."
  }
}

run "new_destination" {
  command = plan

  variables {
    create_destination_bucket = true
    destination_zone          = "US-EAST-04A"
  }

  assert {
    condition     = length(coreweave_object_storage_bucket.destination) == 1 && coreweave_object_storage_bucket.destination[0].zone == "US-EAST-04A"
    error_message = "Create one destination in the requested zone."
  }
  assert {
    condition     = jsondecode(coreweave_object_storage_bucket_policy.destination[0].policy).Statement[0].Resource == ["arn:aws:s3:::example-reports/inventory/*"]
    error_message = "Scope inventory writer access to the report prefix."
  }
  assert {
    condition     = jsondecode(coreweave_object_storage_bucket_policy.destination[0].policy).Statement[2].Principal.CW == "arn:aws:iam::example-org:coreweave/example-user"
    error_message = "Retain report access for the Terraform caller."
  }
}

run "reject_empty_zone" {
  command = plan

  variables {
    destination_zone = ""
  }

  expect_failures = [var.destination_zone]
}

run "new_destination_retention_default" {
  command = plan
  variables {
    create_destination_bucket = true
  }
  assert {
    condition     = coreweave_object_storage_bucket_lifecycle_configuration.reports[0].rule[0].expiration.days == 7 && coreweave_object_storage_bucket_lifecycle_configuration.reports[0].rule[0].filter.prefix == "inventory/"
    error_message = "New destinations must expire only inventory/ objects after seven days by default."
  }
  assert {
    condition     = contains(jsondecode(coreweave_object_storage_bucket_policy.destination[0].policy).Statement[1].Action, "s3:PutLifecycleConfiguration") && contains(jsondecode(coreweave_object_storage_bucket_policy.destination[0].policy).Statement[1].Action, "s3:GetLifecycleConfiguration")
    error_message = "The caller needs lifecycle read and write permissions."
  }
}

run "existing_destination_retention_unmanaged" {
  command = plan
  assert {
    condition     = length(coreweave_object_storage_bucket_lifecycle_configuration.reports) == 0
    error_message = "Existing lifecycle rules must remain untouched by default."
  }
}

run "existing_destination_retention_opt_in" {
  command = plan
  variables {
    manage_report_retention = true
    report_retention_days   = 14
  }
  assert {
    condition     = coreweave_object_storage_bucket_lifecycle_configuration.reports[0].rule[0].expiration.days == 14 && coreweave_object_storage_bucket_lifecycle_configuration.reports[0].bucket == "example-reports"
    error_message = "Explicit opt-in must apply the requested retention to the existing destination."
  }
}

run "new_destination_retention_opt_out" {
  command = plan
  variables {
    create_destination_bucket = true
    manage_report_retention   = false
  }
  assert {
    condition     = length(coreweave_object_storage_bucket_lifecycle_configuration.reports) == 0
    error_message = "Allow retention management to be disabled for a new destination."
  }
}

run "reject_zero_retention" {
  command = plan
  variables {
    report_retention_days = 0
  }
  expect_failures = [var.report_retention_days]
}

run "reject_fractional_retention" {
  command = plan
  variables {
    report_retention_days = 1.5
  }
  expect_failures = [var.report_retention_days]
}
