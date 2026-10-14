<!--
SPDX-FileCopyrightText: 2026 CoreWeave, Inc.
SPDX-License-Identifier: MIT
-->

# CAIOS Explorer onboarding

Run this Terraform project to enable inventory reporting and the CAIOS catalog for existing buckets. Follow the [onboarding guide](caios-explorer-onboarding.md) for destination setup, authentication, import, and verification.

The project manages one inventory configuration per source bucket. Group source buckets and destinations in `inventory_by_zone`. Each zone uses an existing destination by default; set `create_destination_bucket = true` in its entry to create a bucket and policy. Prepare source permissions before applying it.

The source and destination buckets must be in the same CAIOS Availability Zone. Use a separate destination for each zone. One root configuration can manage multiple zones through `modules/inventory`; verify existing bucket locations before applying it.

Authenticate Terraform by loading `COREWEAVE_API_TOKEN` from your secret manager. Alternatively, set `TF_VAR_coreweave_api_token` for the sensitive root input wired to the provider. See [authentication](caios-explorer-onboarding.md#authenticate-terraform) for precedence and discovery credentials.

Run commands from `storage/caios-explorer-onboarding`. Choose either setup path:

- **Manual:** copy `terraform.tfvars.example` to `terraform.tfvars`, edit the zone entries, then run `terraform plan`.
- **Discovery:** install Boto3 and generate a JSON variable file using your AWS profile:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/discover_inventory.py --profile "<aws-profile>" \
  --zone US-EAST-01A --zone US-EAST-03A \
  --destination-prefix "<org-id>-inventory" --output inventory.tfvars.json
terraform init
terraform plan -var-file=inventory.tfvars.json -out=onboarding.tfplan
```

Replace `<aws-profile>` with your configured AWS profile name and `<org-id>` with your CoreWeave organization ID. Use Python 3.10 or later for discovery. Pass `--zone` once for one zone, repeat it for multiple zones, or omit it for all zones. Use `--include` and `--exclude` to select source names. Review generated destinations and skipped-bucket errors before applying. The [onboarding guide](caios-explorer-onboarding.md#configure-terraform) covers both paths, permissions, and endpoint configuration. Run `terraform init` before the first plan in either path.

| Asset | Purpose |
| --- | --- |
| `scripts/discover_inventory.py` | Boto3 bucket discovery with zone filters and Terraform JSON generation |
| `requirements.txt` | Python discovery dependencies |
| `main.tf` | Provider configuration and one module instance per zone |
| `modules/inventory/` | Reusable inventory resources, optional destination bucket, and policy for one zone |
| `variables.tf` | Zone map and shared report settings |
| `outputs.tf` | Inventory configurations grouped by zone and source bucket |
| `terraform.tfvars.example` | Source buckets and report settings |
| `policies/` | Permission statements for bucket administrators to merge into existing policies |
| `.gitignore` | Excludes local state, plans, and environment values |

For existing destinations, prepare permissions before applying Terraform. Policy files contain statement fragments with `<PLACEHOLDERS>`. Replace the placeholders and merge the statements into the complete policy's `Statement` array. Preserve existing grants and review explicit denies before applying the complete policy. The destination reader fragments grant access to your inventory reports.

Commit `.terraform.lock.hcl` after `terraform init` to retain the selected provider version and checksums. Use your organization's protected Terraform state backend for shared operation.

New destinations receive inventory-writer permissions and management/report access for the Terraform caller. Add other readers to the managed policy as needed. Terraform applies the policy before enabling inventory. Keep the same Terraform identity for subsequent runs, or review the caller grants when changing identities.

New destinations use `prevent_destroy` to block bucket deletion or replacement while the resource remains configured. Switching `create_destination_bucket` off also schedules bucket deletion and is blocked. Coordinate a state transfer to retain the bucket under another project. Managed lifecycle rules expire report objects independently of bucket deletion protection.

Run the root and module tests with Terraform 1.7 or later. The mocked provider checks single-zone and multi-zone routing, invalid groupings, destination creation, and report permissions without creating remote resources.

```sh
terraform init -backend=false
terraform test
terraform -chdir=modules/inventory init -backend=false
terraform -chdir=modules/inventory test
```

New destinations expire objects under `inventory/` after seven days by default. Set `report_retention_days` to change the age for all managed destinations. Each zone can set `manage_report_retention`: it defaults to true for new destinations and false for existing destinations. Existing lifecycle rules need review before opting in because Terraform manages the full lifecycle configuration. See [report retention](caios-explorer-onboarding.md#retain-inventory-reports-for-seven-days) for permissions, imports, and versioned destinations.

Run discovery tests with `python3 -m unittest discover -s tests -p 'test_*.py'`. Activate the virtual environment first. The tests use Botocore stubs for SDK responses.
