# Citadel

Emailing on the web all running locally on the CDN server. No internet connection required.

Email, collaboration, groupware, and content management -
up and running in minutes, on your own hardware or in the cloud.

## Installation

Citadel is provided with an easy to install script provided by the creators of citadel. The commands below is to install the app.

```sh
sudo -s

curl https://easyinstall.citadel.org/install | bash
```

The command will install all the dependencies and will help you configure the app. Below are the configurations that is required:

1. Username should be admin

2. Password should be cdn

3. Everything else should remain the default.

4. Set the ports to ```2000``` and ```2001``` for the http and https.

The app would run on [http://localhost:2000](http://localhost:2000/)
