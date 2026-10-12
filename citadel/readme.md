# Existing mail integration

The Office Suite's Mail card opens the server's existing Citadel WebCit mailbox. The main installer **does not install, update, remove or reconfigure Citadel**, preserving the current mail setup. See the [root README](../README.md) for the complete suite, installation and configuration.

The default mail port is 2000. Set `--mail-port` when installing the suite to match your existing WebCit HTTP port. Local mailbox access can work on the LAN without internet; delivery to or receipt from external email services depends on your mail server's network and configuration. The suite does not configure external mail delivery or manage mailbox accounts.

`mail_install.sh` is a separate legacy convenience helper that downloads and runs Citadel's upstream installer. It is not part of the portable suite archive and is never called by the root installer. For a new mail server, follow the [official Citadel documentation](https://www.citadel.org/) and choose your own administrator credentials. The former shared example password is no longer recommended or documented here.

Mail remains outside the Craft update panel. Manage it through its existing administrator and operating-system procedures.

The installer records and retains your mail port across reruns, unless `--mail-port` explicitly changes it. Both the Mail link and readiness check use that saved port. Office, OC4D and mail ports must be distinct; invalid or conflicting settings are rejected.
