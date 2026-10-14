# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

output "inventory_configurations" {
  description = "Inventory configuration details grouped by zone and source bucket."
  value = {
    for zone, inventory in module.inventory : zone => inventory.inventory_configurations
  }
}
