#!/bin/bash

# Display a heading for the CDN Word installation
tput setaf 6
toilet -f big "Installing CDN Word" --gay
tput sgr0

# Define home directory
HOME_DIR="$HOME/etherpad-lite"

# Step 1: Clone the Etherpad-Lite repository into the home directory and install dependencies
echo "Cloning Etherpad-Lite repository into the home directory and installing dependencies..."
sudo npm install -g pnpm
if [ ! -d "$HOME_DIR" ]; then
  git clone -b master https://github.com/ether/etherpad-lite.git "$HOME_DIR"
fi

cd "$HOME_DIR"
pnpm i
pnpm run build:etherpad

# Step 2: Install Abiword for exporting/importing documents (optimized for Raspberry Pi)
echo "Installing Abiword for document export/import..."
sudo apt-get update
sudo apt-get install abiword -y  # Abiword is compatible with Raspberry Pi ARM architecture

# Step 3: Setup SQLite database
echo "Setting up SQLite database..."
pnpm add sqlite3 -w

# Step 4: Setup logging files and directories in the home directory
echo "Setting up log files for the service in $HOME_DIR..."
sudo mkdir -p /var/etherpad/
sudo touch /var/etherpad/etherpad.log
sudo touch /var/etherpad/etherpad-error.log

# Step 5: Copy service file and start the service
echo "Setting up Etherpad as a systemd service..."
sudo cp "$HOME_DIR/etc/systemd/system/etherpad.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable etherpad.service
sudo systemctl start etherpad.service

# Step 6: Install necessary plugins for CDN use
echo "Installing necessary plugins for CDN usage..."
cd "$HOME_DIR"
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

# Final message
tput setaf 2
echo "CDN Word installation completed successfully on Raspberry Pi!"
tput sgr0
