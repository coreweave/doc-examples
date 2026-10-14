<!--
SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
SPDX-License-Identifier: MIT
-->

# Inventory for one CAIOS zone

Use this module to manage inventory configurations for existing source buckets in one CAIOS Availability Zone. Supply `source_buckets`, `destination_bucket`, and `destination_zone`; confirm every bucket is in that zone. Set `create_destination_bucket = true` to create the destination and its policy before enabling inventory.

Configure the CoreWeave provider in the calling root. The [root example](../../main.tf) calls this module with `for_each` over a zone map and passes shared report settings. Separate roots can reuse the module for different organizations or credentials.

The module manages destination policies for newly created buckets. Existing destination permissions remain in their current management workflow. New buckets retain `prevent_destroy`, and inventory configurations depend on the destination policy.

The `inventory_configurations` output maps each source bucket to its inventory name, report destination, prefix, format, and enablement. See [variables.tf](variables.tf) for report settings and defaults.

Report retention defaults to seven days under `inventory/` for new destinations. `manage_report_retention` defaults to the value of `create_destination_bucket`; set it explicitly to opt in or out. `report_retention_days` accepts positive whole days. The lifecycle resource manages the complete destination configuration, so preserve existing rules before opting in for an existing bucket. Current-object expiration leaves noncurrent versions to any separately configured version-expiration rules.
