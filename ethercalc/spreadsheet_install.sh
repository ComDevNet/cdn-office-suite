#!/bin/bash

# Display a heading for the CDN Spreadsheet installation
tput setaf 6
toilet -f big "Installing CDN Spreadsheet" --gay
tput sgr0

echo "Starting CDN Spreadsheet (EtherCalc) installation..."

# Step 1: Create logging directory and files
echo "Setting up logging for EtherCalc..."
sudo mkdir -p /var/ethercalc/
sudo touch /var/ethercalc/ethercalc.log
sudo touch /var/ethercalc/ethercalc-error.log

# Step 2: Install EtherCalc globally
echo "Installing EtherCalc..."
sudo npm i -g ethercalc

# Step 3: Configure EtherCalc as a system service
echo "Configuring EtherCalc as a systemd service..."
sudo cp etc/systemd/system/ethercalc.service /etc/systemd/system/ethercalc.service

# Step 4: Enable and start the EtherCalc service
echo "Starting EtherCalc service..."
sudo systemctl daemon-reload
sudo systemctl enable ethercalc.service
sudo systemctl start ethercalc.service

# Completion message
tput setaf 2
echo "CDN Spreadsheet (EtherCalc) installed and started successfully!"
tput sgr0
