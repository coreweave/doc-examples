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

data "coreweave_caller_identity" "current" {
  count = var.create_destination_bucket ? 1 : 0
}

resource "coreweave_object_storage_bucket" "destination" {
  count = var.create_destination_bucket ? 1 : 0

  name = var.destination_bucket
  zone = var.destination_zone

  lifecycle {
    prevent_destroy = true
  }
}

locals {
  manage_report_retention = coalesce(var.manage_report_retention, var.create_destination_bucket)
  destination_bucket      = var.create_destination_bucket ? coreweave_object_storage_bucket.destination[0].name : var.destination_bucket
  caller_principal        = var.create_destination_bucket ? "arn:aws:iam::${data.coreweave_caller_identity.current[0].organization_id}:coreweave/${data.coreweave_caller_identity.current[0].principal_id}" : null
}

resource "coreweave_object_storage_bucket_policy" "destination" {
  count = var.create_destination_bucket ? 1 : 0

  bucket = local.destination_bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowInventoryWriter"
        Effect    = "Allow"
        Principal = { CW = "arn:aws:iam::static:role/static/inventory" }
        Action    = ["s3:PutObject", "s3:AbortMultipartUpload"]
        Resource  = ["arn:aws:s3:::${local.destination_bucket}/inventory/*"]
      },
      {
        Sid       = "AllowCallerManageDestination"
        Effect    = "Allow"
        Principal = { CW = local.caller_principal }
        Action = [
          "s3:ListBucket",
          "s3:GetBucketPolicy",
          "s3:DeleteBucketPolicy",
          "s3:GetBucketLocation",
          "s3:GetBucketTagging",
          "s3:GetLifecycleConfiguration",
          "s3:PutLifecycleConfiguration",
          "s3:DeleteBucket",
        ]
        Resource = ["arn:aws:s3:::${local.destination_bucket}"]
      },
      {
        Sid       = "AllowCallerManageReports"
        Effect    = "Allow"
        Principal = { CW = local.caller_principal }
        Action    = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"]
        Resource  = ["arn:aws:s3:::${local.destination_bucket}/inventory/*"]
      },
    ]
  })
}

resource "coreweave_object_storage_bucket_inventory" "catalog" {
  for_each = var.source_buckets

  depends_on = [coreweave_object_storage_bucket_policy.destination]

  bucket                   = each.value
  name                     = var.inventory_name
  enabled                  = var.enabled
  included_object_versions = var.included_object_versions
  optional_fields          = var.optional_fields

  schedule {
    frequency = var.frequency
  }

  destination {
    bucket {
      bucket_arn = "arn:aws:s3:::${local.destination_bucket}"
      format     = var.report_format
      prefix     = "inventory/"
    }
  }
}

resource "coreweave_object_storage_bucket_lifecycle_configuration" "reports" {
  count = local.manage_report_retention ? 1 : 0

  bucket     = local.destination_bucket
  depends_on = [coreweave_object_storage_bucket_policy.destination]

  rule {
    id     = "expire-inventory-reports"
    status = "Enabled"

    filter {
      prefix = "inventory/"
    }

    expiration {
      days = var.report_retention_days
    }
  }
}
