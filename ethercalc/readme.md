# Ethercalc

Ethercalc is a web-based spreadsheet that allows multiple users to edit a spreadsheet at the same time. It is a self-hosted application that can be used to create and edit spreadsheets.

## Setup to get service running

Run the following commands

```sh
sudo mkdir /var/ethercalc/

sudo touch /var/ethercalc/ethercalc.log

sudo touch /var/ethercalc/ethercalc-error.log

sudo npm i -g ethercalc
```

## Running the Tool

```sh
ethercalc
```

The application runs on port ```8000```.

Copy the [service file](/ethercalc/etc/systemd/system/ethercalc.service) to ```/etc/systemd/system/``` then run the following commands

```sh
sudo systemctl daemon-reload

sudo systemctl enable ethercalc.service

sudo systemctl start ethercalc.service

```
