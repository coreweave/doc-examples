#!/bin/bash

# Function to execute a command with verbose output
function executeCommand {
    echo -e "\n$(date +"%Y-%m-%d %H:%M:%S") - Executing: $1"
    eval $1
}

# Update package lists
executeCommand "sudo apt-get update"

# Install unzip
executeCommand "sudo apt install unzip"

# Download Intel NVM update package
executeCommand "wget https://downloadmirror.intel.com/786057/700Series_NVMUpdatePackage_v9_30.zip"

# Unzip the downloaded file
executeCommand "unzip 700Series_NVMUpdatePackage_v9_30.zip"

# Extract the contents of the tar.gz file
executeCommand "tar xzf 700Series_NVMUpdatePackage_v9_30_Linux.tar.gz"

# Navigate to the Linux_x64 directory
executeCommand "cd 700Series/Linux_x64/"

# Change permissions for nvmupdate64e
executeCommand "chmod 755 nvmupdate64e"

# Run the nvmupdate64e with sudo privileges
executeCommand "sudo ./nvmupdate64e"

echo "Script execution completed."
