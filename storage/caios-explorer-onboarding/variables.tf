# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

variable "coreweave_api_token" {
  description = "CoreWeave API token (CW-SECRET-...). Set through TF_VAR_coreweave_api_token or use the provider's COREWEAVE_API_TOKEN environment variable."
  type        = string
  sensitive   = true
  default     = null
}

variable "inventory_by_zone" {
  description = "Inventory destinations and source buckets grouped by their actual CAIOS Availability Zone."
  type = map(object({
    source_buckets            = set(string)
    destination_bucket        = string
    create_destination_bucket = optional(bool, false)
    manage_report_retention   = optional(bool)
  }))
  nullable = false

  validation {
    condition     = length(var.inventory_by_zone) > 0 && alltrue([for zone in keys(var.inventory_by_zone) : length(trimspace(zone)) > 0 && zone == trimspace(zone)])
    error_message = "Provide at least one zone, with nonempty zone keys without surrounding whitespace."
  }

  validation {
    condition     = length(flatten([for config in values(var.inventory_by_zone) : tolist(config.source_buckets)])) == length(distinct(flatten([for config in values(var.inventory_by_zone) : tolist(config.source_buckets)])))
    error_message = "Each source bucket must appear in only one zone."
  }

  validation {
    condition     = length(distinct([for config in values(var.inventory_by_zone) : config.destination_bucket])) == length(var.inventory_by_zone)
    error_message = "Each zone must use a different destination bucket."
  }
}

variable "enabled" {
  description = "Set false to stop future reports while retaining the inventory configuration."
  type        = bool
  default     = true
}

variable "inventory_name" {
  description = "Inventory configuration name, unique within each source bucket."
  type        = string
  default     = "daily-inventory"
}

variable "report_format" {
  description = "Format of inventory reports delivered to your destination."
  type        = string
  default     = "CSV"

  validation {
    condition     = contains(["CSV", "TSV", "JSON", "ORC", "Parquet"], var.report_format)
    error_message = "Choose CSV, TSV, JSON, ORC, or Parquet."
  }
}

variable "frequency" {
  description = "Inventory report schedule."
  type        = string
  default     = "Daily"

  validation {
    condition     = contains(["Daily", "Weekly"], var.frequency)
    error_message = "Choose Daily or Weekly."
  }
}

variable "included_object_versions" {
  description = "Object versions to include in your reports."
  type        = string
  default     = "All"

  validation {
    condition     = contains(["All", "Current"], var.included_object_versions)
    error_message = "Choose All or Current."
  }
}

variable "optional_fields" {
  description = "Additional fields in your reports. Set null to omit additional fields."
  type        = set(string)
  default     = ["Size", "LastModifiedDate"]
}

variable "report_retention_days" {
  description = "Days before objects under inventory/ expire when report retention is managed."
  type        = number
  default     = 7
  nullable    = false

  validation {
    condition     = var.report_retention_days >= 1 && floor(var.report_retention_days) == var.report_retention_days
    error_message = "Report retention must be a positive whole number of days."
  }
}
