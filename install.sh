#!/bin/bash

# Function to check and install required packages for text formatting and colors
function install_dependencies {
  echo "Checking for required packages..."
  # Check if figlet and toilet (for colorful headings) are installed
  if ! command -v figlet &> /dev/null
  then
    echo "Installing figlet..."
    sudo apt-get install -y figlet
  fi
  if ! command -v toilet &> /dev/null
  then
    echo "Installing toilet..."
    sudo apt-get install -y toilet
  fi
}

# Function to display the colorful heading
function display_heading {
  # Use tput to set colors
  tput setaf 6  # Set color to cyan
  toilet -f big "CDN Office Suite" --gay  # Display colorful and fun text
  tput sgr0     # Reset colors
}

# Function to display the menu
function display_menu {
  tput setaf 3  # Set color to yellow for description
  echo "Welcome to the CDN Office Suite installer."
  echo "This script is used to install CDN Office Suite."
  echo "You can choose to install all tools or only selected ones."
  tput sgr0  # Reset color

  echo
  echo "1. Install Full CDN Office Suite"
  echo "2. Install CDN Word"
  echo "3. Install CDN Spreadsheet"
  echo "4. Install CDN Email"
  echo "5. Exit"
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
}

# Function to install Spreadsheet tool
function install_spreadsheet {
  echo "Installing CDN Spreadsheet..."
  # Simulate the installation process
  sleep 2
  echo "CDN Spreadsheet installed successfully!"
}

# Function to install email tool
function install_email {
  echo "Installing CDN email..."
  # Simulate the installation process
  sleep 2
  echo "CDN email installed successfully!"
}

# Main script logic
install_dependencies
clear  # Clear the terminal for better visibility
display_heading
display_menu

# Main loop to handle user choices
while true; do
  read -p "Enter your choice (1-5): " choice
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
      echo "Exiting CDN Office Suite installer. Goodbye!"
      exit 0
      ;;
    *)
      echo "Invalid option, please select a valid number (1-5)."
      ;;
  esac
done
