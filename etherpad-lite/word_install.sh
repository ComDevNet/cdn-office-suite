#!/bin/bash

# Display a heading for the CDN Word installation
tput setaf 6
toilet -f big "Installing CDN Word" --gay
tput sgr0

echo "Starting CDN Word (Etherpad) installation..."

# Step 1: Navigate to home directory and install pnpm
cd ~
sudo npm install -g pnpm

# Step 2: Clone the Etherpad repository
echo
echo "Cloning the Etherpad repository..."
git clone -b master https://github.com/ether/etherpad-lite.git
cd etherpad-lite

# Step 3: Install Etherpad dependencies and build
echo
echo "Installing dependencies for Etherpad..."
pnpm i
pnpm run build:etherpad

# Step 4: Update system and install Abiword for document export/import
echo
echo "Installing Abiword for document export/import..."
sudo apt-get update
sudo apt-get install -y abiword

# Step 5: Copy settings.json file into Etherpad directory
echo
echo "Copying settings.json to Etherpad directory..."
sudo cp /home/pi/cdn-office-suite/etherpad-lite/settings.json /home/pi/etherpad-lite/settings.json

# Step 6: Set up SQLite database support
echo
echo "Setting up SQLite database..."
cd /home/pi/etherpad-lite/
pnpm add sqlite3 -w

# Step 7: Set up logging directory and files
echo
echo "Setting up logging for Etherpad..."
sudo mkdir -p /var/etherpad/
sudo touch /var/etherpad/etherpad.log
sudo touch /var/etherpad/etherpad-error.log

# Step 8: Configure Etherpad as a system service
echo
echo "Configuring Etherpad as a systemd service..."
sudo cp /home/pi/cdn-office-suite/etherpad-lite/etc/systemd/system/etherpad.service /etc/systemd/system/etherpad.service

# Step 9: Install Etherpad plugins
echo
echo "Installing necessary plugins for Etherpad..."
pnpm run install-plugins ep_aa_file_menu_toolbar
pnpm run install-plugins ep_align
pnpm run install-plugins ep_embedded_hyperlinks2
pnpm run install-plugins ep_font_family
pnpm run install-plugins ep_font_color
pnpm run install-plugins ep_font_size
pnpm run install-plugins ep_headings2
pnpm run install-plugins ep_image_upload
pnpm run install-plugins ep_set_title_on_pad
pnpm run install-plugins ep_spellcheck

# Step 10: Enable and start Etherpad service
echo
echo "Starting Etherpad service..."
sudo systemctl daemon-reload
sudo systemctl enable etherpad.service
sudo systemctl start etherpad.service

# Completion message
tput setaf 2
echo "CDN Word (Etherpad) installed and started successfully!"
tput sgr0
echo
