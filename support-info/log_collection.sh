#!/bin/bash

# Check if the script is run with sudo
check_sudo() {
  if [[ $EUID -ne 0 ]]; then
    echo "This script must be run with sudo. Please try again with sudo."
    exit 1
  fi
}

check_sudo

start_time=$SECONDS
timestamp=$(date +"%Y-%m-%d_%H-%M-%S_%Z")

echo "*******************************************************"
echo "*                                                     *"
echo "*   Welcome to the CoreWeave Log Collection Tool      *"
echo "*                                                     *"
echo "*   This tool gathers necessary logs for support.     *"
echo "*   Logs will be compressed - please attach to your   *"
echo "*   Jira ticket.                                      *"
echo "*                                                     *"
echo "*   Log Collection Tool v2.2                          *"
echo "*   Build Date: 15 April 2026                         *"
echo "*******************************************************"

read -p "Enter the JIRA ticket number or the system serial number: " jira_ticket

# Validate input — only allow alphanumeric, hyphens, underscores, and dots
# This also blocks $(...), backticks, and other shell metacharacters that
# would be evaluated when the string is interpolated into bash -c commands.
if [[ -z "$jira_ticket" ]]; then
  echo "ERROR: No ticket number or serial provided. Exiting."
  exit 1
fi
if [[ ! "$jira_ticket" =~ ^[[:alnum:]_.-]+$ ]]; then
  echo "ERROR: Ticket/serial must contain only letters, numbers, hyphens, underscores, and dots."
  exit 1
fi

hostname_short=$(hostname -s 2>/dev/null || echo "unknown")
collect_dir="${jira_ticket}_${hostname_short}_${timestamp}"

mkdir -p "$collect_dir"

# Tee all subsequent stdout to run-summary.txt so the console output is preserved in the tarball.
# Write a header first (the banner printed above predates the directory, so capture it manually).
run_log="$collect_dir/run-summary.txt"
{
  echo "CoreWeave Log Collection Tool v2.2"
  echo "Run started: $timestamp"
  echo "Ticket/serial: $jira_ticket"
  echo "Hostname: $(hostname -f 2>/dev/null)"
  echo "=================================================="
} > "$run_log"
exec > >(tee -a "$run_log")

# Create an empty file named after the node serial number
node_serial=$(dmidecode -s system-serial-number 2>/dev/null | tr -d '[:space:]' | tr -cd '[:alnum:]_.-')
# Reject placeholder values that dmidecode returns on unconfigured systems
if [[ -n "$node_serial" && ! "$node_serial" =~ ^(NotSpecified|ToBeFilledByO\.E\.M\.|TBD|Default|SystemSerialNumber|None)$ ]]; then
  touch "$collect_dir/$node_serial"
fi

# Temp file for stderr capture; cleaned up on any exit
stderr_tmp=$(mktemp)
warnings=()
trap 'rm -f "$stderr_tmp"' EXIT
trap 'echo ""; echo "Interrupted. Partial logs preserved in: $PWD/$collect_dir"; exit 130' INT
trap 'echo ""; echo "Interrupted. Partial logs preserved in: $PWD/$collect_dir"; exit 143' TERM

# Define and run commands
commands=(
  # === InfiniBand / RDMA ===
  "ibstat > $collect_dir/ibstat.txt"
  "ibstatus > $collect_dir/ibstatus-output.txt"
  "ibv_devinfo > $collect_dir/ibv-devinfo.txt"
  "ibdiagnet > $collect_dir/ibdiagnet_output.txt"
  "ibnetdiscover > $collect_dir/ibnetdiscover.txt"
  "sminfo > $collect_dir/sminfo.txt"
  "ofed_info > $collect_dir/ofed-info.txt"
  "mlxfwmanager --query > $collect_dir/mlxfwmanager.txt || true"
  "mst start > $collect_dir/mst-start.txt 2>&1"
  "mst status -v > $collect_dir/mst-status-v.txt"
  "lspci | grep -i Mellanox > $collect_dir/mellanox-lspci.txt || true"

  # === NVIDIA GPU ===
  "nvidia-smi > $collect_dir/nvidia-smi.txt"
  "nvidia-smi -q > $collect_dir/nvidia-smi-query-full.txt"
  "nvidia-smi -q -x > $collect_dir/nvidia-smi-query-xml.txt"
  "nvidia-smi --query-gpu=gpu_name,gpu_bus_id,vbios_version --format=csv > $collect_dir/nvidia-smi-query-summary.txt"
  "nvidia-smi topo -m > $collect_dir/nvidia-topo.txt"
  "nvidia-smi nvlink -s > $collect_dir/nvlink-statuses.txt"
  "nvidia-smi nvlink -e > $collect_dir/nvlink-errors.txt"
  "nvidia-smi nvlink -c > $collect_dir/nvlink-capabilities.txt"
  "nvidia-smi -q -d CLOCK > $collect_dir/nvidia-smi-clocks.txt"
  "nvidia-smi -q -d row_remapper > $collect_dir/nvidia-smi-row-remap.txt"
  "nvidia-debugdump -l > $collect_dir/nvidia-debugdump-l.txt"
  "modinfo nvidia > $collect_dir/drivers.txt"
  "systemctl status --no-pager -l nvidia-fabricmanager > $collect_dir/nvidia-fabricmanager-status.txt || true"
  "journalctl -u nvidia-fabricmanager --no-pager | tail -n 5000 > $collect_dir/fabricmanager-journal.txt"

  # === System Info ===
  "hostname -f > $collect_dir/hostname.txt"
  "uname -a > $collect_dir/uname.txt"
  "cat /etc/os-release > $collect_dir/os-release.txt"
  "lscpu > $collect_dir/lscpu.txt"
  "cat /proc/meminfo > $collect_dir/meminfo.txt"
  "free -h > $collect_dir/free.txt"
  "lshw -C display > $collect_dir/biosvers.txt"
  "numactl --hardware > $collect_dir/numactl-hardware.txt"
  "lstopo > $collect_dir/lstopo-output.txt || true"
  "uptime > $collect_dir/uptime.txt"
  "lsmod > $collect_dir/lsmod.txt"
  "systemctl list-units --failed --no-pager > $collect_dir/systemctl-failed.txt"
  "dmidecode -t memory > $collect_dir/dmidecode-memory.txt"
  "dpkg -l 2>/dev/null | grep -iE 'nvidia|cuda|mlnx|ofed' > $collect_dir/gpu-packages.txt || true; rpm -qa 2>/dev/null | grep -iE 'nvidia|cuda|mlnx|ofed' >> $collect_dir/gpu-packages.txt || true"

  # === Kernel / PCI ===
  "dmesg -T > $collect_dir/dmesg-log.txt"
  "dmesg -T | grep NVRM > $collect_dir/dmesg-nvrm.txt || true"
  "dmesg -T | grep -i nvidia > $collect_dir/dmesg-grep-nvidia.txt || true"
  "dmesg -T | grep -iE 'aer|pcie error' > $collect_dir/dmesg-pcie-errors.txt || true"
  "lspci > $collect_dir/lspci.txt"
  "lspci -vvv > $collect_dir/lspci-vvv.txt"
  "lspci -t > $collect_dir/lspci-tree.txt"

  # === Network ===
  "ip addr list > $collect_dir/ip-addr-list.txt"
  "ip route show > $collect_dir/ip-route.txt"

  # === Storage ===
  "nvme list > $collect_dir/nvme-output.txt"

  # === IPMI ===
  "ipmitool sel list > $collect_dir/ipmitool-sel.txt"
  "ipmitool sel elist > $collect_dir/ipmitool-sel-elist.txt"
  "ipmitool sel time get > $collect_dir/ipmitool-sel-time.txt"
  "ipmitool fru print > $collect_dir/ipmitool-fru.txt"
  "ipmitool lan print > $collect_dir/ipmitool-lan.txt"
  "ipmitool sensor list > $collect_dir/ipmitool-sensor.txt"
  "ipmitool sdr elist > $collect_dir/ipmitool-sdr-elist.txt"
  "ipmitool user list 1 > $collect_dir/ipmitool-user-list.txt"

  # === Journals ===
  "journalctl -b --no-pager | tail -n 50000 > $collect_dir/journalctl-boot.txt"
  "journalctl -x --no-pager | tail -n 50000 > $collect_dir/journalctl-xe.txt"
)

# Execute commands with progress counter, timeout, and stderr capture
total=${#commands[@]}
count=0
for cmd in "${commands[@]}"; do
  count=$((count + 1))
  echo "[$count/$total] $cmd"
  timeout 180 bash -c "$cmd" 2>"$stderr_tmp"
  exit_code=$?
  if [ $exit_code -eq 124 ]; then
    msg="Timed out (180s): $cmd"
    echo "  WARNING: $msg"
    cat "$stderr_tmp"
    warnings+=("$msg")
  elif [ $exit_code -ne 0 ]; then
    msg="Failed (exit $exit_code): $cmd"
    echo "  WARNING: $msg"
    cat "$stderr_tmp"
    warnings+=("$msg")
  fi
done

# ibdiagnet iblinkinfo (side-effect file, copy only if it exists and has content)
if [ -s /var/tmp/ibdiagnet2/ibdiagnet2.iblinkinfo ]; then
  cp /var/tmp/ibdiagnet2/ibdiagnet2.iblinkinfo "$collect_dir/ibdiagnet2.iblinkinfo.txt"
fi

# Syslog — try /var/log/syslog (Debian/Ubuntu) then /var/log/messages (RHEL/Rocky)
for f in /var/log/syslog /var/log/messages; do
  if [ -f "$f" ]; then
    cp "$f" "$collect_dir/syslog.txt"
    break
  fi
done

# SMART data — discover all storage devices via smartctl --scan (single scan, reused)
echo "[*] Collecting SMART data..."
smart_scan=$(smartctl --scan 2>&1)
{
  echo "=== smartctl --scan ==="
  echo "$smart_scan"
} > "$collect_dir/nvme-smartctl.txt"
while read -r dev _rest; do
  [[ "$dev" =~ ^/dev/ ]] || continue
  echo "" >> "$collect_dir/nvme-smartctl.txt"
  echo "===== smartctl -a $dev =====" >> "$collect_dir/nvme-smartctl.txt"
  timeout 180 smartctl -a "$dev" >> "$collect_dir/nvme-smartctl.txt" 2>&1
  ret=$?
  if [ $ret -eq 124 ]; then
    msg="Timed out (180s): smartctl -a $dev"
    echo "  WARNING: $msg"
    warnings+=("$msg")
  fi
done <<< "$smart_scan"

# IPMI LAN channels
echo "[*] Collecting IPMI LAN channel info..."
for channel in 1 2 3; do
  echo "=== channel $channel ===" >> "$collect_dir/ipmitool-lan-print-channels.txt"
  timeout 180 ipmitool lan print $channel >> "$collect_dir/ipmitool-lan-print-channels.txt" 2>&1
  if [ $? -eq 124 ]; then
    msg="Timed out (180s): ipmitool lan print $channel"
    echo "  WARNING: $msg"
    warnings+=("$msg")
  fi
done

# InfiniBand port error counters (from sysfs)
echo "[*] Collecting InfiniBand port counters..."
for counters_dir in /sys/class/infiniband/*/ports/*/counters; do
  [ -d "$counters_dir" ] || continue
  echo "=== $counters_dir ===" >> "$collect_dir/ib-port-counters.txt"
  grep -r . "$counters_dir" 2>/dev/null >> "$collect_dir/ib-port-counters.txt"
done

# Crash dumps — skip any file over 100MB
echo "[*] Collecting crash dumps..."
mkdir -p "$collect_dir/crash-dumps"
find /var/crash -maxdepth 1 -type f -size -100M -exec cp {} "$collect_dir/crash-dumps/" \; 2>/dev/null || true

# Fabricmanager log files
echo "[*] Collecting fabricmanager logs..."
if [ -d "/var/log/nvidia-fabricmanager" ]; then
  mkdir -p "$collect_dir/fabricmanager-logs"
  cp /var/log/nvidia-fabricmanager/* "$collect_dir/fabricmanager-logs/" 2>/dev/null || true
fi

# master.log
echo "[*] Building master.log..."
{
  echo "CoreWeave Log Collection"
  echo "Collected on:  $timestamp"
  echo "Hostname:      $(hostname -f 2>/dev/null)"
  echo "Node serial:   ${node_serial:-unknown}"
  echo "=================================================="
  ipmitool fru print 2>/dev/null
  echo "BMC $(ipmitool mc info 2>/dev/null | awk -F': ' '/Firmware Revision/ {print "firmware version:", $2}')"
  echo "BIOS $(dmidecode -t bios 2>/dev/null | awk -F': ' '/Version/ {print "version:", $2}')"
  echo "=================================================="
  echo "If any GPUs fell off the bus (Xid79) - will be shown below"
  dmesg -T 2>/dev/null | grep NVRM
  echo "If no GPUs fell off the bus - no data will be shown above."
  echo "=================================================="
  echo "VBIOS Versions:"
  nvidia-smi -q 2>/dev/null | grep -i Vbios | awk -F': ' '{print $2}'
  echo "=================================================="
  echo "GPU count (healthy node has eight):"
  nvidia-smi -q 2>/dev/null | grep -i serial
  echo "=================================================="
  nvidia-smi -L 2>/dev/null
  echo "=================================================="
  echo "Row Remap (For a failure, Yes must appear below):"
  nvidia-smi -q -d row_remapper 2>/dev/null | grep Remapping
  echo "=================================================="
  nvidia-smi --format=csv --query-remapped-rows=timestamp,gpu_serial,remapped_rows.failure,remapped_rows.uncorrectable 2>/dev/null
  echo "=================================================="
  nvidia-smi --format=csv --query-gpu=gpu_name,gpu_bus_id,serial,uuid,ecc.errors.uncorrected.volatile.total,ecc.errors.uncorrected.aggregate.total 2>/dev/null
  echo "=================================================="
  nvidia-smi -q 2>/dev/null | grep 'Single'
  echo "=================================================="
  nvidia-smi -q 2>/dev/null | grep 'Double'
  echo "=================================================="
  lspci 2>/dev/null | grep -i nvidia
  echo "=================================================="

  # GPU Link Speed (dynamically discovered NVIDIA devices)
  echo "GPU link speed:"
  for dev in $(lspci 2>/dev/null | grep -i nvidia | grep -iv bridge | awk '{print $1}'); do
    echo "  $dev $(lspci -s "$dev" -vv 2>/dev/null | grep LnkSta)"
  done
  echo "=================================================="

  # NIC Link Speed (dynamically discovered Mellanox devices)
  echo "NIC card link speed:"
  for dev in $(lspci 2>/dev/null | grep -i mellanox | awk '{print $1}'); do
    echo "  $dev $(lspci -s "$dev" -vv 2>/dev/null | grep LnkSta)"
  done
  echo "=================================================="

  # Collection warnings
  if [ ${#warnings[@]} -gt 0 ]; then
    echo ""
    echo "=== COLLECTION WARNINGS (${#warnings[@]}) ==="
    printf '  - %s\n' "${warnings[@]}"
  fi
} > "$collect_dir/master.log" 2>/dev/null

# Write standalone warnings file for easy visibility
if [ ${#warnings[@]} -gt 0 ]; then
  printf '%s\n' "${warnings[@]}" > "$collect_dir/warnings.txt"
fi

# Compress
tarball_path="$PWD/${jira_ticket}.tar.gz"
if ! tar -czvf "$tarball_path" "$collect_dir" &>/dev/null; then
  echo "ERROR: Failed to create tarball. Raw logs preserved in: $PWD/$collect_dir"
  exit 1
fi
rm -rf "$collect_dir"
chmod a+rw "$tarball_path"

elapsed=$((SECONDS - start_time))

echo ""
echo "=================================================="
echo "Logs saved to:  $tarball_path"
echo "Tarball size:   $(du -sh "$tarball_path" 2>/dev/null | cut -f1)"
echo "Elapsed time:   ${elapsed}s"
if [ ${#warnings[@]} -gt 0 ]; then
  echo ""
  echo "=== WARNINGS (${#warnings[@]}) ==="
  printf '  - %s\n' "${warnings[@]}"
fi
echo "=================================================="
echo "Attach this tarball to your Jira ticket and notify the CoreWeave support team."
