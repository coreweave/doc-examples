#!/bin/bash

# Check if the script is run with sudo
check_sudo() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script must be run with sudo. Please try again with sudo."
    exit 1
  fi
}

# Call the function to check if the script is run with sudo
check_sudo

# current time
timestamp=$(date +"%Y-%m-%d_%H-%M-%S_%Z")


# Display welcome message
echo "*******************************************************"
echo "*                                                     *"
echo "*   Welcome to the CoreWeave Log Collection Tool      *"
echo "*                                                     *"
echo "*   This tool gathers necessary logs for support.     *"
echo "*   Logs will be compressed - please attach to your   *"
echo "*   Jira ticket.                                      *"
echo "*                                                     *"
echo "*   Log Collection Tool v1.5                          *"
echo "*   Build Date: 3 February 2025                       *"
echo "*******************************************************"

# Prompt the user for the JIRA ticket number
read -p "Enter the JIRA ticket number or the system serial number: " jira_ticket

# Create log directory with name of user input from above
mkdir -p "$jira_ticket"

# Define and run commands
commands=(
  "ibstat > $jira_ticket/ibstat.txt"
  "sudo ibdiagnet > $jira_ticket/ibdiagnet_output.txt"
  "sudo touch /var/tmp/ibdiagnet2/ibdiagnet2.iblinkinfo"
  "sudo cp /var/tmp/ibdiagnet2/ibdiagnet2.iblinkinfo $jira_ticket/ibdiagnet2.iblinkinfo.txt"
  "nvidia-smi --query-gpu=gpu_name,gpu_bus_id,vbios_version --format=csv > $jira_ticket/nvidia-smi-query-summary.txt"
  "nvidia-smi -q > $jira_ticket/nvidia-smi-query-full.txt"
  "nvidia-smi > $jira_ticket/nvidia-smi.txt"
  "nvidia-smi nvlink -s  > $jira_ticket/nvlink-statuses.txt"
  "lshw -C display > $jira_ticket/biosvers.txt"
  "modinfo nvidia > $jira_ticket/drvers.txt"
  "dmesg > $jira_ticket/dmesg-log.txt"
  "lspci > $jira_ticket/lspci.txt"
  "lspci -vvv > $jira_ticket/lspci-vvv.txt"
  "nvidia-bug-report.sh > $jira_ticket/nvidia-bug-report.log.gz"
  "sudo mst start"
  "sudo mst status -v > $jira_ticket/mst-status-v.txt"
  "lspci | grep -i Mellanox > $jira_ticket/mellanox-lspci.txt"
  "lstopo > $jira_ticket/lstopo-output.txt"
  "sudo nvme list > $jira_ticket/nvme-output.txt"
  "dmesg | grep NVRM > $jira_ticket/dmesg-nvrm.txt"
  "sudo ipmitool sel list > $jira_ticket/ipmitool-sel.txt"
  "sudo ipmitool fru print > $jira_ticket/ipmitool-fru.txt"
  "sudo ipmitool lan print > $jira_ticket/ipmitool-lan.txt"
  "sudo ipmitool sensor list > $jira_ticket/ipmitool-sensor.txt"
  "sudo systemctl status nvidia-fabricmanager > $jira_ticket/nvidia-fabricmanager-status.txt"
)

# Execute commands
for cmd in "${commands[@]}"; do
  echo "Running the command: $cmd"
  eval "$cmd" &> /dev/null
  echo "Saved output to log file."
done

# Collect additional logs
echo "Gathering some additional logs for CoreWeave..." > $jira_ticket/master.log
echo "Log collected on: $timestamp" >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
sudo ipmitool fru print >> $jira_ticket/master.log
echo "BMC $(sudo ipmitool mc info | awk -F': ' '/Firmware Revision/ {print "firmware version:", $2}')" >> $jira_ticket/master.log
echo "BIOS $(sudo dmidecode -t bios | awk -F': ' '/Version/ {print "version:", $2}')" >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
echo "If any GPUs fell off the bus (Xid79) - will be shown below" >> $jira_ticket/master.log
sudo dmesg | grep NVRM >> $jira_ticket/master.log
echo "If no GPUs fell off the bus - no data will be shown above." >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
# VBIOS Versions
echo "VBIOS Versions:" >> $jira_ticket/master.log
sudo nvidia-smi -q | grep -i Vbios | awk -F': ' '{print $2}' >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
echo "GPU VBIOS check complete." >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
echo "Checking for GPU count." >> $jira_ticket/master.log
echo "A healthy node has eight GPUs below" >> $jira_ticket/master.log
nvidia-smi -q | grep -i serial >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
nvidia-smi -L >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
echo "For a Row Remap Failure, Yes must appear below" >> $jira_ticket/master.log
nvidia-smi -q -d row_remapper | grep Remapping >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
nvidia-smi --format=csv --query-remapped-rows=timestamp,gpu_serial,remapped_rows.failure,remapped_rows.uncorrectable >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
nvidia-smi --format=csv --query-gpu=gpu_name,gpu_bus_id,serial,uuid,ecc.errors.uncorrected.volatile.total,ecc.errors.uncorrected.aggregate.total >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
nvidia-smi -q | grep 'Single' >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
nvidia-smi -q | grep 'Double' >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log
lspci | grep -i nvidia >> $jira_ticket/master.log
echo ================================================== >> $jira_ticket/master.log

# GPU Link Speed
echo "GPU link speed" >> $jira_ticket/master.log
for dev in 19:00.0 1c:00.0 3f:00.0 42:00.0 9b:00.0 9e:00.0 bf:00.0 c2:00.0; do
  sudo lspci -s $dev -vv | grep LnkSta >> $jira_ticket/master.log
done
echo ================================================== >> $jira_ticket/master.log

# NIC Link Speed
echo "NIC card link speed" >> $jira_ticket/master.log
for dev in c1:00.0 c0:00.0 9d:00.0 9c:00.0 41:00.0 40:00.0 1b:00.0 1a:00.0; do
  sudo lspci -s $dev -vv | grep LnkSta >> $jira_ticket/master.log
done
echo ================================================== >> $jira_ticket/master.log


# Compress logs
tarball_path="$PWD/${jira_ticket}.tar.gz"
tar -czvf "$tarball_path" "$jira_ticket" &> /dev/null
rm -rf "$jira_ticket"
chmod a+rw "$tarball_path"

# Completion message
echo "Logs saved to: $tarball_path"
echo "Attach this tarball to Jira Ticket and notify the CoreWeave support team."
