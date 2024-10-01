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

# Display welcome message
echo "Welcome to the CoreWeave Log Collection Tool"
echo "This tool has been designed to help you gather the necessary logs"
echo "requested by our support team. Once collected, these logs will be"
echo "compressed into a tarball, which you can then attach to your support"
echo "JIRA ticket. Thank you for using our tool!"

# Display version information
echo "Log Collection Tool v0.7"

# Prompt the user for the JIRA ticket number
read -p "Enter the JIRA ticket number (example: SDB-2011) or the serial number of the chassis: " jira_ticket

# Define the file names
file_names=(
  "nvidia-smi-query.txt"
  "biosvers.txt"
  "vdinfo.txt"
  "drvers.txt"
  "dmesg-log.txt"
  "lspci.txt"
  "pciview.txt"
  "lspci-tvvv.txt"
  "lspci-vvv.txt"
  "nvidia-bug-report.log.gz"
  "mst-start.txt"
  "mst-status-v.txt"
  "mellanox-lspci.txt"
  "lstopo-output.txt"
  "lstopo-v-output.txt"
)

# Define a function to run commands and save output
run_command() {
  $1 > "$2"
  echo "Executed: $1"
}

# Define commands to run and save output
commands=(
  "nvidia-smi --query"
  "nvidia-smi --query-gpu=gpu_name,gpu_bus_id,vbios_version --format=csv"
  "lshw -C display"
  "modinfo nvidia"
  "dmesg"
  "lspci"
  "lspci -v"
  "lspci -tvvv"
  "lspci -vvv"
  "nvidia-bug-report.sh"
  "sudo mst start"
  "sudo mst status -v"
  "lspci | grep -i Mellanox"
  "lstopo"
  "lstopo -v"
)

# Run commands
for i in "${!commands[@]}"; do
  run_command "${commands[$i]}" "${file_names[$i]}"
done

# Create a directory with the JIRA ticket number
mkdir "$jira_ticket"

# Move the generated files to the directory
for file_name in "${file_names[@]}"; do
  mv "$file_name" "$jira_ticket/"
done

# Define a function to clean up after creating the tarball
cleanup() {
  # Remove the directory and its contents
  rm -rf "$jira_ticket"
}

# Compress the directory
tarball_path="$PWD/$jira_ticket.tar.gz"
tar -czvf "$jira_ticket.tar.gz" "$jira_ticket"

# Clean up the directory
cleanup

# Set permissions on the tarball to make it accessible to all users
chmod a+rw "$jira_ticket.tar.gz"

echo "Logs have been saved to a tarball at $tarball_path"
echo "Please attach this tarball of log files to the Jira Ticket $jira_ticket and notify the CoreWeave support team."
