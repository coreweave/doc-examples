# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    coreweave = {
      source  = "coreweave/coreweave"
      version = "~> 0.22.0"
    }
  }
}

provider "coreweave" {
  token = var.coreweave_api_token
}

module "inventory" {
  source   = "./modules/inventory"
  for_each = var.inventory_by_zone

  source_buckets            = each.value.source_buckets
  destination_bucket        = each.value.destination_bucket
  create_destination_bucket = each.value.create_destination_bucket
  destination_zone          = each.key
  manage_report_retention   = each.value.manage_report_retention
  report_retention_days     = var.report_retention_days

  inventory_name           = var.inventory_name
  enabled                  = var.enabled
  report_format            = var.report_format
  frequency                = var.frequency
  included_object_versions = var.included_object_versions
  optional_fields          = var.optional_fields
}
