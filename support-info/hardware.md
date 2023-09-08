When requested by support, please provide the following information in the attachment:

* BIOS and CPLD Version
* GPU Firmware version, if available.

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
nvdia-bug-report.sh
sudo nvidia-bug-report.sh # Will create a file called nvidia-bug-report.log.gz. Please attach this file to your request.
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