# SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
# SPDX-License-Identifier: MIT

variable "source_buckets" {
  description = "Existing source buckets to inventory."
  type        = set(string)

  validation {
    condition     = length(var.source_buckets) > 0 && alltrue([for name in var.source_buckets : length(trimspace(name)) > 0 && name == trimspace(name) && !startswith(name, "arn:")])
    error_message = "Provide at least one source bucket name, without whitespace or an ARN prefix."
  }
}

variable "destination_bucket" {
  description = "Destination bucket name for your inventory reports, existing or to be created."
  type        = string

  validation {
    condition     = length(trimspace(var.destination_bucket)) > 0 && var.destination_bucket == trimspace(var.destination_bucket) && !startswith(var.destination_bucket, "arn:")
    error_message = "Provide the destination bucket name, without whitespace or an ARN prefix."
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

variable "create_destination_bucket" {
  description = "Create the destination bucket and manage its policy. Defaults to using an existing destination."
  type        = bool
  default     = false
  nullable    = false
}

variable "destination_zone" {
  description = "CAIOS Availability Zone of all source buckets and the destination, including existing destinations."
  type        = string
  nullable    = false

  validation {
    condition     = length(trimspace(var.destination_zone)) > 0 && var.destination_zone == trimspace(var.destination_zone)
    error_message = "Provide a nonempty destination zone without surrounding whitespace."
  }
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

variable "manage_report_retention" {
  description = "Manage the destination's full lifecycle configuration. Defaults to true for new destinations and false for existing destinations."
  type        = bool
  default     = null
}
