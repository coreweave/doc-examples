**Required Information for opening RMA Requests with CoreWeave support**

As part of our support process, please provide the following information in the Jira support ticket to help expedite your RMA request:

* For all issues, please provide the BIOS and CPLD Version, if available.
* For all issues,  please provide the log collection tarball from our automated tool below, or manually collected logs using the commands we provide below.
* For GPU Specific issues, please provide the GPU Firmware version, if available.
* For GPU Specific issues,  please provide the logs from HGX FD, GPU FD through HGX FD, IST through HGX FD or TinyMeg.



**For GPU specific issues - NV will RMA GPUs if any of the four tools show a failure.**

1. HGX FD
2. GPU FD through HGX FD
3. IST through HGX FD
4. TinyMeg

NEW: You can use our automated log collection tool to dump logs and create a tarball to attach to a Jira support ticket.

```bash
sudo bash -c "curl -sSL https://raw.githubusercontent.com/coreweave/doc-examples/main/support-info/log_collection.sh -o log_collection.sh && bash log_collection.sh"
```

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
```
