# Delete cold objects

Supporting script for [Delete cold objects](https://docs.coreweave.com/products/storage/object-storage/using-object-storage/delete-cold-objects)
on docs.coreweave.com.

`delete_cold_objects.py` is a single-file, staged workflow for safely identifying
and deleting cold objects in CoreWeave AI Object Storage when the source of truth
for the data lives elsewhere. It uses Inventory Reporting, a quarantine buffer
window, and versioning as layers of defense against deleting recently accessed
objects.

## Stages

| Subcommand   | Stage   | What it does                                                        |
| ------------ | ------- | ------------------------------------------------------------------ |
| `identify`   | Stage 1 | Read an inventory report and list cold candidates.                 |
| `quarantine` | Stage 2 | Tag candidates and persist state for the buffer window.            |
| `delete`     | Stage 3 | Re-check access times, enable versioning, delete confirmed keys.   |
| `recover`    | Stage 4 | Restore mistakenly deleted keys before cleanup runs.               |
| `cleanup`    | Stage 4 | Permanently remove recovery copies and delete markers.            |

## Configuration

Set these environment variables before running:

```bash
export ACCESS_KEY_ID="[ACCESS-KEY-ID]"
export SECRET_ACCESS_KEY="[SECRET-ACCESS-KEY]"
export BUCKET="[BUCKET-NAME]"
# Optional, with defaults shown:
export ENDPOINT_URL="https://cwobject.com"   # LOTA: http://cwlota.com
export REGION="US-EAST-04A"
```

## Usage

```bash
python delete_cold_objects.py identify --inventory inventory.csv --threshold-days 90
python delete_cold_objects.py quarantine
# ...wait the buffer window (for example, 30 days)...
python delete_cold_objects.py delete --inventory inventory_fresh.csv
# ...wait the recovery window (for example, 30 days)...
python delete_cold_objects.py cleanup
```

The inventory CSV is headerless. Confirm the column order against your report's
`manifest.json` (`fileSchema`) and pass `--fields` if it differs from the
documented default.

## Requirements

- Python 3.9 or later
- `boto3`
