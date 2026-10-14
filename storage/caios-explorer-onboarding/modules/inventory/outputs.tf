# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

output "inventory_configurations" {
  description = "Inventory configuration details."
  value = {
    for name, report in coreweave_object_storage_bucket_inventory.catalog : name => {
      inventory_name     = report.name
      destination_bucket = local.destination_bucket
      prefix             = "inventory/"
      format             = var.report_format
      enabled            = report.enabled
    }
  }
}
