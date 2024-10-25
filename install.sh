#!/bin/bash

# Function to check and install required packages for text formatting and colors
function install_dependencies {
  echo "Checking for required packages..."
  if ! command -v figlet &> /dev/null; then
    echo "Installing figlet..."
    sudo apt-get install -y figlet
  fi
  if ! command -v toilet &> /dev/null; then
    echo "Installing toilet..."
    sudo apt-get install -y toilet
  fi
  echo "Required packages installed successfully!"
  echo 
  echo "Making all the scripts executable..."
  chmod +x etherpad-lite/word_install.sh
  chmod +x ethercalc/spreadsheet_install.sh
  chmod +x citadel/mail_install.sh
}

# Function to display the colorful heading
function display_heading {
  tput setaf 6  # Set color to cyan
  toilet -f big "CDN Office Suite" --gay
  tput sgr0     # Reset colors
}

# Function to display the menu
function display_menu {
  tput setaf 3  # Set color to yellow for description
  echo "Welcome to the CDN Office Suite installer."
  echo "This script installs the CDN Office Suite. Choose to install all tools or select individual ones."
  tput sgr0  # Reset color

  echo 
  echo "1. Install Full CDN Office Suite"
  echo "2. Install CDN Word"
  echo "3. Install CDN Spreadsheet"
  echo "4. Install CDN Email"
  echo "5. Update Script"
  echo "6. Exit"
}

# Function to install full suite
function install_full_suite {
  echo "Installing Full CDN Office Suite..."
  install_word
  install_spreadsheet
  install_email
}

# Function to install Word tool
function install_word {
  echo "Installing CDN Word..."
  ./etherpad-lite/word_install.sh
  echo "CDN Word installed successfully!"
  echo 
}

# Function to install Spreadsheet tool
function install_spreadsheet {
  echo "Installing CDN Spreadsheet..."
  ./ethercalc/spreadsheet_install.sh
  echo "CDN Spreadsheet installed successfully!"
  echo 
}

# Function to install email tool
function install_email {
  echo "Installing CDN Email..."
  ./citadel/mail_install.sh
  echo "CDN Email installed successfully!"
  echo 
}

# Function to update the script
function update_script {
  echo "Updating the script..."
  git fetch origin main
  Git reset --hard origin/main
  chmod +x etherpad-lite/word_install.sh
  chmod +x ethercalc/spreadsheet_install.sh
  chmod +x citadel/mail_install.sh
  chmod +x install.sh
  echo "Script updated successfully!"
}

# Main script logic
install_dependencies
clear  # Clear the terminal for better visibility
display_heading

# Main loop to handle user choices
while true; do
  display_menu
  read -p "Enter your choice (1-6): " choice
  case $choice in
    1)
      install_full_suite
      ;;
    2)
      install_word
      ;;
    3)
      install_spreadsheet
      ;;
    4)
      install_email
      ;;
    5)
      update_script
      ;;
    6)
      echo "Exiting CDN Office Suite installer. Goodbye!"
      exit 0
      ;;
    *)
      echo "Invalid option, please select a valid number (1-6)."
      ;;
  esac
done
