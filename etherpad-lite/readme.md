# Setting up etherpad-lite

Clone the repo then run the following commands

```sh
npm install -g pnpm

git clone -b master https://github.com/ether/etherpad-lite.git

cd etherpad-lite

pnpm i

pnpm run build:etherpad

pnpm run prod
```

Exit the process with ```ctrl + c``` then run the following command to start the service

## Install abiword with the following commands

Abiword give ether pad the ability to export and import documents as MS Word and PDF's

Also make sure the settings.json is in the project root

```sh
sudo apt-get update

sudo apt-get install abiword
```

## Setup to get service running

Run the following commands

```sh
sudo mkdir /var/etherpad/

sudo touch /var/etherpad/etherpad.log

sudo touch /var/etherpad/etherpad-error.log
```

Copy the [service file](/etherpad-lite/etc/systemd/system/etherpad.service) to ```/etc/systemd/system/``` then run the following commands

```sh
sudo systemctl daemon-reload

sudo systemctl enable etherpad.service

sudo systemctl start etherpad.service

```

## Run the following commands to install the plugins, or use the admin panel to install them

These plugins are what makes it good for CDN use

```sh
cd etherpad-lite

pnpm run plugins install ep_aa_file_menu_toolbar

pnpm run plugins install ep_align

pnpm run plugins install ep_embedded_hyperlinks2

pnpm run plugins install ep_font_family

pnpm run plugins install ep_font_color

pnpm run plugins install ep_font_size

pnpm run plugins install ep_headings2

pnpm run plugins install ep_image_upload

pnpm run plugins install ep_set_title_on_pad
```
