# CDN Office Suite

This is a CDN Office Suite that is designed to be used on CDN servers. The suite includes the following:

- [Etherpad Lite](/etherpad-lite/readme.md)

- [Ethercalc](/ethercalc/readme.md)

- [Citadel](/citadel/readme.md)

The installation process is as simple as running a the install script.

You would have to make the install script executable before running it.

```sh
chmod =x install.sh
```

Then run the install script.

```sh
./install.sh
```

After installation, you can access the services on the following ports:

- Etherpad Lite: 9001

- Ethercalc: 8000

- Citadel: 2000

The services are designed to run on the same server and can be accessed on the same domain.

For easier access to the services, upload the [module](/cdn_office_suite/). This will allow you to easily access the services.
