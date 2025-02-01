# RMA Request Process

As part of our support process, the following information is required when opening an RMA request with CoreWeave support. Please provide the following information in the Jira support ticket to help expedite your RMA request:

## All issues

For all issues, please provide:

- BIOS version,
- CPLD version if available, and
- system logs from :
  - the log collection tarball from [the automated tool below](#automated-log-collection)

## GPU Specific Issues

In addition, for GPU specific issues, please provide:

- the GPU firmware version if available
- logs from any of the following tools:
  - HGX FD
  - GPU FD through HGX FD
  - IST through HGX FD
  - TinyMeg

For GPU specific issues, NV will RMA the GPUs if any of those four tools show a failure.

## Automated Log Collection

You can use [this automated log collection tool](https://raw.githubusercontent.com/coreweave/doc-examples/main/support-info/log_collection.sh) to dump logs and create a tarball to attach to a Jira support ticket.

```bash
sudo bash -c "curl -sSL https://raw.githubusercontent.com/coreweave/doc-examples/main/support-info/log_collection.sh -o log_collection.sh && bash log_collection.sh"
```

