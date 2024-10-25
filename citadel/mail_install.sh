#!/bin/bash

# Display a heading for the CDN Email installation
tput setaf 6
toilet -f big "Installing CDN Email" --gay
tput sgr0

echo "Starting CDN Email (Citadel) installation..."

# Run Citadel installation command
sudo -s <<EOF
curl https://easyinstall.citadel.org/install | bash
EOF

# Completion message
tput setaf 2
echo "CDN Email (Citadel) installed successfully!"
tput sgr0
