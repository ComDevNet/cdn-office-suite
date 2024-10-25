#!/bin/bash

# Display a heading for the CDN Spreadsheet installation
tput setaf 6
toilet -f big "Installing CDN Spreadsheet" --gay
tput sgr0

echo "Starting CDN Spreadsheet (EtherCalc) installation..."

# Move to the Home Screen
cd ~

# Step 1: Create logging directory and files
echo
echo "Setting up logging for EtherCalc..."
sudo mkdir -p /var/log/ethercalc/
sudo touch /var/log/ethercalc/ethercalc.log
sudo touch /var/log/ethercalc/ethercalc-error.log

# Step 2: Install EtherCalc globally
echo
echo "Installing EtherCalc..."
sudo npm i -g ethercalc

# Step 3: Configure EtherCalc as a system service
echo
echo "Configuring EtherCalc as a systemd service..."
sudo cp /home/pi/cdn-office-suite/ethercalc/etc/systemd/system/ethercalc.service /etc/systemd/system/ethercalc.service

# Step 4: Enable and start the EtherCalc service
echo
echo "Starting EtherCalc service..."
sudo systemctl daemon-reload
sudo systemctl enable ethercalc.service
sudo systemctl start ethercalc.service

# Completion message
tput setaf 2
echo "CDN Spreadsheet (EtherCalc) installed and started successfully!"
tput sgr0
