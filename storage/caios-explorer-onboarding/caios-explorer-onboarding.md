<!--
SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
SPDX-License-Identifier: MIT
-->

# Enable the CAIOS Explorer for a bucket

During the private preview, your organization must be on the CAIOS Explorer allowlist. Enable inventory reporting on your CoreWeave AI Object Storage (CAIOS) bucket to make its metadata available in CAIOS Explorer. Your inventory reports continue to arrive in the destination you choose, using your configured report settings.

If inventory reporting is already enabled, keep your existing configuration. For a bucket without inventory reporting, use the [Terraform sample](README.md) or follow the [inventory configuration instructions](https://docs.coreweave.com/products/storage/object-storage/buckets/inventory-reporting/configure).

## Prerequisites

- Your organization is on the private-preview allowlist. Contact CoreWeave Support to request access. Organizations outside the allowlist continue to receive inventory reports, but CAIOS Explorer shows no data.
- Your user has the `Object Storage Catalog Viewer` role to view catalog data.
- An existing CAIOS source bucket.
- An existing destination bucket, or a globally unique name and CAIOS Availability Zone for a new report bucket.
- Permission to manage inventory configurations on the source bucket and configure access to the destination. Creating a destination also requires permission to list and create buckets and manage their policies.
- Terraform 1.5 or later and a CoreWeave API token when using the sample.

The source and destination buckets must be in the same CAIOS Availability Zone. Group source buckets by zone in `inventory_by_zone`, with one destination per zone. The map records your intended grouping; confirm the actual bucket locations before applying Terraform.

## Prepare report permissions

Grant your Terraform identity `s3:GetInventoryConfiguration` and `s3:PutInventoryConfiguration` on the source bucket. Grant the CoreWeave inventory service `s3:PutObject` and `s3:AbortMultipartUpload` on the destination report prefix. Give report readers permission to list the destination and read reports. Follow the [bucket policy setup](https://docs.coreweave.com/products/storage/object-storage/buckets/inventory-reporting/configure#set-bucket-access-policies).

For an existing destination, the sample includes [permission statements](policies/) for bucket administrators. Replace the placeholders and merge them into your existing policies, preserving other required grants. Apply the destination permissions before enabling inventory reporting.

When creating a destination with the sample, Terraform grants the inventory service report-write access and the authenticated Terraform caller access to manage the bucket and reports. Add grants to the managed policy for any additional report readers. Source bucket permissions remain a prerequisite.

## Configure Terraform

From the repository root, enter the Terraform example directory:

```sh
cd storage/caios-explorer-onboarding
```

Define `inventory_by_zone` by editing `terraform.tfvars` or generating `inventory.tfvars.json` with the discovery tool. Both paths support one or multiple zones.

### Option 1 Define the variables manually

Create your manual variable file from the example:

```sh
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with one entry per CAIOS Availability Zone. For a single zone with an existing destination:

```hcl
inventory_by_zone = {
  "US-EAST-04A" = {
    source_buckets     = ["your-source-bucket"]
    destination_bucket = "your-inventory-report-bucket"
  }
}

inventory_name = "daily-inventory"
report_format  = "CSV"
enabled        = true
```

Use the actual zone of the source and destination buckets as the map key. To create a destination, set `create_destination_bucket = true` inside that zone's entry and choose a globally unique destination name. Terraform creates the bucket in the zone named by the key. Existing destinations remain under your current policy-management workflow by default.

For multiple zones, add entries to the same map:

```hcl
inventory_by_zone = {
  "US-EAST-04A" = {
    source_buckets     = ["your-east-source-bucket"]
    destination_bucket = "your-east-inventory-report-bucket"
  }
  "US-WEST-09A" = {
    source_buckets            = ["your-west-source-bucket"]
    destination_bucket        = "your-new-west-inventory-report-bucket"
    create_destination_bucket = true
  }
}
```

Each source bucket belongs to one zone entry, and each zone uses a different destination. The root calls `modules/inventory` once per zone. Use one root configuration per organization and credential set; separate deployments can reuse the same module.

### Option 2 Discover buckets with Boto3

Use Python 3.10 or later to install the discovery dependencies in a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The helper uses Boto3 with your shared AWS profile or its default credential chain. Your identity needs `s3:ListAllMyBuckets` to list buckets and `s3:ListBucket` on selected buckets for `HeadBucket`. Boto3 reads the zone through `HeadBucket` with hostname-based addressing; your AWS configuration stays unchanged. See the [Boto3 configuration reference](https://docs.aws.amazon.com/boto3/latest/guide/configuration.html).

Replace `<aws-profile>` with your configured AWS profile name and `<org-id>` with your CoreWeave organization ID.

Discover one zone:

```sh
python scripts/discover_inventory.py \
  --profile "<aws-profile>" \
  --zone US-EAST-02A \
  --destination-prefix "<org-id>-inventory" \
  --output inventory.tfvars.json
```

Repeat `--zone` to discover multiple zones:

```sh
python scripts/discover_inventory.py \
  --profile "<aws-profile>" \
  --zone US-EAST-02A --zone US-WEST-09A \
  --destination-prefix "<org-id>-inventory" \
  --output inventory.tfvars.json
```

Omit `--zone` to include every discovered zone. Zone matching ignores letter case. Discovery lists all buckets and checks locations before applying the zone filter. Narrow source names before those lookups with repeatable, quoted patterns such as `--include 'training-*'` or `--exclude '*-backups'`.

The helper uses the S3 endpoint from your profile or environment. Add `--endpoint-url https://cwobject.com` to override it. Discovery performs read-only requests and writes local variables; it creates no buckets or inventory configurations.

Destination names follow `<destination-prefix>-<zone>`, such as `<org-id>-inventory-us-east-02a`. A matching existing destination is excluded from the source list and reused after its zone is verified. Otherwise, the generated entry sets `create_destination_bucket = true`. Choose a prefix unique to your organization. Edit the output to reuse differently named destinations, setting their creation flags to `false` and confirming their zones.

Failed lookups and unsupported zone formats are skipped and reported on stderr. An unverifiable destination also excludes its zone's sources. The helper reports requested zones without usable sources. Successful buckets produce a map and a zero exit status; no usable sources or a bucket-listing failure produces an error and no output file. An existing output file is preserved.

Review the generated `inventory.tfvars.json`, destination creation flags, and skipped-bucket summary before planning. Exclude unrelated report buckets or other buckets you want to leave out. New destinations receive the default seven-day retention. Keep shared report settings in `terraform.tfvars` if needed, with the zone map defined only in the generated JSON file.

### Shared report settings

The sample creates daily reports under `inventory/`. Choose `report_format`, `frequency`, `included_object_versions`, and `optional_fields` for the reports you want to receive. These settings, `inventory_name`, and `enabled` apply to every zone. Keep `enabled = true` to enable inventory reporting. Catalog access also requires the private-preview prerequisites above.

## Authenticate Terraform

Load your CoreWeave API token (`CW-SECRET-...`) into `COREWEAVE_API_TOKEN` through your secret manager or shell environment before running Terraform. The provider uses that token to obtain temporary S3 credentials. See [CoreWeave Terraform authentication](https://docs.coreweave.com/platform/terraform).

The root also accepts the sensitive `coreweave_api_token` input, wired to `provider.coreweave.token`. To supply that input through Terraform's environment-variable mechanism, use `TF_VAR_coreweave_api_token`. For example, if your secret manager has populated `COREWEAVE_API_TOKEN`:

```sh
export TF_VAR_coreweave_api_token="$COREWEAVE_API_TOKEN"
```

`COREWEAVE_API_TOKEN` takes precedence when both are set. Keep tokens out of `.tf` and `.tfvars` files; use your CI secret store for automated runs.

Boto3 discovery uses S3 credentials from its AWS profile or default credential chain. Configure that profile and the Terraform token for the same organization.

## Retain inventory reports for seven days

New destination buckets receive a lifecycle rule that expires objects under `inventory/` after seven days. Reserve that prefix for disposable reports: the rule applies to every object beneath it, including reports already present. Bucket deletion protection (`prevent_destroy`) allows lifecycle expiration of individual objects.

Set the shared retention period in `terraform.tfvars`:

```hcl
report_retention_days = 7
```

Set `manage_report_retention = false` inside a zone entry to keep its lifecycle configuration unmanaged. Existing destinations default to unmanaged retention so their current rules remain in place. To enable retention on an existing destination, set `manage_report_retention = true` in its zone entry and grant the Terraform identity `s3:GetLifecycleConfiguration` and `s3:PutLifecycleConfiguration` on that bucket.

Terraform manages the destination's complete lifecycle configuration. If the bucket has existing rules, keep lifecycle management in its current project and add an `inventory/` expiration rule there. To transfer management to this module, preserve every required rule in `modules/inventory/main.tf` and import the existing configuration before applying:

```sh
terraform import \
  'module.inventory["US-EAST-04A"].coreweave_object_storage_bucket_lifecycle_configuration.reports[0]' \
  'your-inventory-report-bucket'
```

The sample configures current-object expiration. Versioned destinations need additional noncurrent-version expiration rules to reclaim older versions; manage those rules with the destination's lifecycle configuration. See the [lifecycle resource reference](https://registry.terraform.io/providers/coreweave/coreweave/latest/docs/resources/object_storage_bucket_lifecycle_configuration).

Choose a longer retention period if you need older reports for analysis. The rule sets an expiration age; lifecycle processing determines when eligible objects are removed. Setting `enabled = false` pauses report generation while lifecycle expiration continues. Changing managed retention to `false` plans deletion of the lifecycle configuration, so review the plan before applying.

## Apply the configuration

```sh
terraform init
terraform fmt -check
terraform validate
```

For manually defined variables in `terraform.tfvars`:

```sh
terraform plan -out=onboarding.tfplan
```

For a map generated by the discovery tool:

```sh
terraform plan -var-file=inventory.tfvars.json -out=onboarding.tfplan
```

Apply the reviewed plan from either path:

```sh
terraform apply onboarding.tfplan
```

Review the plan before applying it. Expect one inventory configuration per source bucket. When destination creation is enabled, also expect one bucket, its policy, and a lifecycle configuration for each zone that enables creation with default retention. Terraform applies that policy before enabling inventory reporting.

To manage an existing inventory configuration with the sample, match its current settings in Terraform and import it before planning. Preserve any existing prefix or filter by adapting `modules/inventory/main.tf` before import. Replace the zone, bucket, and configuration name in this command:

```sh
terraform import \
  'module.inventory["US-EAST-04A"].coreweave_object_storage_bucket_inventory.catalog["your-source-bucket"]' \
  'your-source-bucket:daily-inventory'
```

When using the generated JSON map, add `-var-file=inventory.tfvars.json` immediately after `terraform import`.

Keep each inventory configuration in one Terraform state. If another project manages it, update that project or coordinate a state transfer with its owner.

Inspect the configured destinations by zone and source bucket:

```sh
terraform output -json inventory_configurations
```

## Verify enablement

Check that your inventory configuration is enabled. If you use the AWS CLI, configure S3 credentials and run:

```sh
aws --endpoint-url https://cwobject.com s3api get-bucket-inventory-configuration \
  --bucket your-source-bucket \
  --id daily-inventory
```

Confirm that `IsEnabled` is `true` and the destination matches your report bucket.

Allow time for the first scheduled report, then check your destination for its manifest and data files. See [report verification](https://docs.coreweave.com/products/storage/object-storage/buckets/inventory-reporting/configure#check-your-inventory-report). Catalog data becomes available after processing and reflects periodic updates to bucket metadata.

Open the CAIOS Explorer dashboard in the [Storage dashboards folder](https://cks-grafana.coreweave.com/dashboards/f/storage/). The dashboard is open to all users. Viewing its data requires the `Object Storage Catalog Viewer` role and an organization on the private-preview allowlist.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Terraform authentication fails | Verify your CoreWeave API token. |
| Enabling inventory returns access denied | Check source inventory permissions and destination report-write permissions. |
| Inventory reports are missing | Confirm enablement and the destination, then check report permissions. |
| Inventory reports arrive but CAIOS Explorer shows no data | Confirm your organization is on the private-preview allowlist and your user has the `Object Storage Catalog Viewer` role. If data remains unavailable, contact CoreWeave Support with your organization, source bucket, zone, and time inventory was enabled. |
| CAIOS Explorer data access is denied | Verify your user has the `Object Storage Catalog Viewer` role. |

Exclude tokens and Terraform state files from support requests.

## Disable inventory reporting

Set `enabled = false` to pause reports across all configured zones, review the Terraform plan, and apply it to stop future inventory reports. Contact CoreWeave Support before disabling reports if you depend on continued catalog updates. Existing reports remain in your destination bucket until you remove them or a retention policy expires them.

Terraform protects a destination created by this sample with `prevent_destroy`. Renaming it, changing its zone, or switching creation off can produce a blocked destruction plan. Plan a state transfer or migration before changing destination ownership. Lifecycle rules continue to expire report objects while bucket deletion protection is enabled.
