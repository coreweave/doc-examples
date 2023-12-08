**NV will RMA GPUs if any of the four tools show a failure.**
1. HGX FD
2. GPU FD through HGX FD
3. IST through HGX FD
4. TinyMeg

When requested by support, please provide the following information in the attachment:

* BIOS and CPLD Version
* GPU Firmware version, if available.

NEW: You can use our automated log collection tool to dump logs and create a tarball to attach to a Jira support ticket.

```bash
sudo bash -c "curl -sSL https://raw.githubusercontent.com/coreweave/doc-examples/main/support-info/log_collection.sh -o log_collection.sh && bash log_collection.sh"
```
Please attach the output of the following commands to the request:

```bash
ipmitool fru print 0
ipmitool sel elist last 100 # Or screenshot BMC WebGUI Event Logs
ipmitool sdr elist # Or screenshot of BMC WebGUI sensor logs
nvidia-smi >> smiqv.txt
```

or

```bash
nvidia-smi > nvidia-smi.txt
nvidia-smi -q >> smifull.txt
```
or

```bash
nvidia-smi --query > nvidia-smi-query.txt
nvidia-smi --query-gpu=gpu_name,gpu_bus_id,vbios_version --format=csv >> biosvers.txt
nvidia-smi -q | grep -i serial >> nvidiaserials.txt
sudo lshw -C display >> vdinfo.txt
modinfo nvidia >> drvers.txt
sudo nvidia-bug-report.sh # Please attach nvidia-bug-report.log.gz to your request.
dmesg > dmesg-log.txt
dmesg -T | grep -i xid # or applicable error type
dmesg -T | grep -i xid >> dmesg xid
lspci >> lspci.txt
lspci -v | grep -I nvidia >> pciview.txt
lspci | grep -I nvidia
lspci | grep -i nvidia
lspci -tvvv
lspci -vvv | grep -E "^..:|LnkCap:|LnkSta:"
```
