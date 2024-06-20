# RMA Request Process

As part of our support process, the following information is required when opening an RMA request with CoreWeave support. Please provide the following information in the Jira support ticket to help expedite your RMA request:

## All issues

For all issues, please provide:

- BIOS version,
- CPLD version if available, and
- system logs from either:
  - the log collection tarball from [the automated tool below](#automated-log-collection), **or**
  - manually collected logs using [the commands provided below](#manual-log-collection)

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

## Manual Log Collection

For manual log collection - please run all of the below commands and attach the output of the following commands to the Jira support ticket:

```bash
#IPMI Tool Info
ipmitool fru print 0
ipmitool sel elist last 100 # Or screenshot BMC WebGUI Event Logs
ipmitool sdr elist # Or screenshot of BMC WebGUI sensor logs
```
and

```bash
# NVIDIA GPU Info
nvidia-smi --query-gpu=gpu_name,gpu_bus_id,vbios_version --format=csv > gpu_info.txt
nvidia-smi -q | grep -i serial >> gpu_info.txt
modinfo nvidia >> gpu_info.txt

# System Info
sudo lshw -C display > display_info.txt
lspci > lspci_info.txt
lspci -v | grep -I nvidia >> lspci_info.txt
lspci -tvvv >> lspci_info.txt

# Logs and Error Checking
dmesg > dmesg_log.txt
dmesg -T | grep -i xid > xid_errors.txt
sudo nvidia-bug-report.sh # Attach nvidia-bug-report.log.gz to your request

# Full NVIDIA SMI and System Logs
nvidia-smi > nvidia_smi.txt
nvidia-smi -q >> nvidia_smi.txt


# Infiniband
sudo mst start
sudo mst status -v
lspci | grep -i Mellanox

```
