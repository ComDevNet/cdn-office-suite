# CDN Office Suite

An offline-friendly workspace for writing, spreadsheets, presentations, PDFs, illustration, CAD and photo editing, with a link to the server's existing mail. The launcher uses official app artwork, warm colours, keyboard focus states, responsive cards and reduced-motion support. There is no sidebar.

## Included tools

- **Wordcraft** - write documents, stories and notes. Replaces Etherpad Lite.
- **Gridcraft** - work with spreadsheets and numbers. Replaces Ethercalc.
- **Deckcraft** - create presentations.
- **PDFcraft** - read and work with PDF documents.
- **Vectorcraft** - create vector drawings and illustrations.
- **CADcraft** - sketch and draft designs.
- **Photocraft** - edit photographs and images.
- **Mail** - opens the existing Citadel WebCit service. The suite installer does not install, update or reconfigure mail.

The seven Craft tools run as WebAssembly applications in each user's browser. The Pi serves their files; document processing primarily uses the user's device. Save your work to your device before closing tabs. These upstream applications are alpha software and do not provide a shared document store or simultaneous collaborative editing through this suite. Not every upstream import/export format has been tested.

## What the installer does

The root `install.sh` is the installer for **all seven Craft apps**, their shared Python host and the OC4D launcher. It installs missing Python 3/iproute2 through apt, validates the existing OC4D service, discovers its service user and website directory, checks free storage and port availability, and installs verified web releases without compiling Rust or Node applications.

It stages releases, verifies checksums, validates ZIP paths and expanded size, precompresses suitable assets, switches active release links atomically, retains a previous release, backs up runtime/configuration, installs official app favicons and launcher artwork, connects OC4D authentication, enables the office host and OC4D at boot, and checks all seven app pages before legacy removal. A failed installation restores tracked configuration and release pointers. Recognized Etherpad/Ethercalc services, application folders, binaries, logs, installer fragments and fallback pages are removed after replacement health checks. Existing documents are archived privately first. Symlinks and unrecognized legacy installations require inspection; shared runtimes and databases are retained.

Rerunning the installer skips bundled application versions that are already installed or newer, while refreshing the host and launcher. It briefly restarts OC4D. The private authentication secret is reused; if a new one is required, users must sign out and sign in once.

## Requirements

- An existing OC4D installation running as a dedicated non-root systemd user.
- Linux with systemd; tested on Raspberry Pi 4, ARM64, Debian 12, 4 GB RAM.
- Python 3.10 or newer and `ss` from iproute2. Missing packages need apt/internet on supported Debian-based systems.
- At least 1 GB free disk space; more is needed for repeated releases and backups.
- Distinct office, OC4D and mail ports. Defaults: 8769, 3000 and 2000.
- The office port must be reachable from user devices, and every server IP/hostname used by visitors must appear in `--hosts`.

The installer targets existing OC4D appliances. It does not install OC4D itself, configure HTTPS/firewalls, provide a public internet deployment or guarantee compatibility with arbitrary Linux distributions and authentication systems. HTTPS OC4D needs a matching HTTPS proxy for the office host to avoid mixed-content blocking.

## Install or upgrade another server

Use the portable archive in `dist/`. The current installer revision is **v0.10.0**; this is separate from each app's own version.

```sh
sha256sum -c cdn-office-suite-installer-v0.10.0.tar.gz.sha256
tar -xzf cdn-office-suite-installer-v0.10.0.tar.gz
cd cdn-office-suite-installer
sudo bash install.sh --dry-run
sudo bash install.sh
```

The archive includes seven checksum-verified web releases and official icons. App installation can run offline when system prerequisites already exist. A Git source checkout without bundled ZIP files downloads stable upstream releases. `--online` explicitly selects current stable releases instead of bundled versions.

```sh
sudo bash install.sh --oc4d-service oc4d.service \
  --website-dir /home/pi/oc4d-server/workspaces/website \
  --install-dir /home/pi/cdn-office-suite \
  --hosts 192.168.191.89,cdn.local --port 8769 \
  --oc4d-port 3000 --mail-port 2000
```

Ports are recorded in `<install-dir>/deckcraft-data/installation.json` and retained on installer reruns. Omitted port flags reuse the recorded office, OC4D and mail ports; defaults apply only to a first installation. Older installations migrate their existing launcher/service settings. Change a port deliberately with its explicit flag. Duplicate, invalid or unreadable port settings are rejected. The host refuses to start if its runtime ports differ from the saved installation, or if its listening port is occupied; it never chooses another port. Launcher and update requests use explicit validated ports and stop when configuration is missing rather than falling back to the page's port. Mail status checks use the configured mail port.

All seven Craft apps share the office port, with separate `/wordcraft/`, `/gridcraft/`, `/deckcraft/`, `/pdfcraft/`, `/vectorcraft/`, `/cadcraft/` and `/photocraft/` routes. They do not each need a separate listening service. OC4D keeps its own port and Citadel keeps its existing mail port. Manifest validation prevents building/installing a distribution that omits a Craft app.

All options: `--oc4d-service`, `--website-dir`, `--install-dir`, `--hosts`, `--port`, `--oc4d-port`, `--mail-port`, `--online`, `--dry-run`. Run `bash install.sh --help` for argument details.

## Open the suite

Open `/modules/cdn_office_suite/index.html` on the OC4D server. Each Craft link opens `http://SERVER:8769/APP/index.html`; mail opens the configured existing mail port. The launcher reports ready, unavailable and maintenance states. Each app tab receives its own official favicon through the host, including upstream builds that omit one.

## Superadmin updates

The separate Updates page is available only to logged-in OC4D server superadmins. The protected panel, release checks, update approval and rollback all validate the signed OC4D session and current database role on the server. Hiding controls is not the authorization boundary. Normal users, unsigned tokens and the retired administrator key cannot update apps.

1. Check an app for a stable release. Checking never installs anything.
2. Review the release and approve its specific version.
3. Follow its saved stage, percentage, download size, attempt count and retry status.

One app updates at a time. Approval and progress are saved before acceptance. Updates continue when the browser closes or loses connection; reconnecting restores progress. Unfinished jobs resume after the office service restarts. Temporary download/network failures retry automatically with backoff, using the exact approved release. Interrupted downloads restart from the beginning. Invalid checksums or changed release files stop for administrator review. Release checking itself requires internet and reports failures for another check.

The affected app stays in maintenance while queued, updating or waiting for a retry. New visitors are blocked and existing tabs are locked while retaining their loaded content. Save before an update; reopen afterward to use the new release. Other apps remain available. Rollback restores the retained previous release after explicit superadmin approval.

## Why there is only a deckcraft code folder

`deckcraft/` is the **shared office host**, named after the first app installed. It is not a Deckcraft-only application source tree. `server.py` registers all seven tools, and `bootstrap.py` installs their official release archives. Separate Rust source checkouts are unnecessary.

Repository layout:

- `cdn_office_suite/` - launcher, Updates shell, configuration and official artwork.
- `deckcraft/` - shared host, installer, safe legacy cleanup, protected update panel, maintenance script and tests.
- `deckcraft/bundled/` - release manifest, checksum files and downloaded ZIPs. Large ZIP/checksum files are ignored by Git but included in the portable archive.
- `citadel/` - optional legacy mail helper and documentation; not invoked by the suite installer.
- `third_party/` and `THIRD_PARTY.md` - upstream licenses and attribution.
- `dist/` - generated portable installer, checksum and verification artifacts; ignored by Git.

Installed layout under `<install-dir>`:

- `deckcraft/` - Python runtime, protected panel, maintenance script and `icons/` for all seven apps.
- `deckcraft-data/releases/` and `deckcraft-data/current` - Deckcraft releases and active link.
- `deckcraft-data/APP/releases/`, `current` and `previous` - each of the six other apps.
- `deckcraft-data/APP/job.json` and `checked.json` - saved jobs and reviewed release metadata; Deckcraft uses the data root.
- `deckcraft-data/installation.json` - saved office/OC4D/mail ports and the complete app registry.
- `deckcraft-data/oc4d-auth.env`, `service.env`, `operations.lock` - private authentication, service configuration and shared update lock.
- `backups/` - installer/runtime backups.
- `legacy-data-backups/` - private archives of documents from retired tools.

The launcher is copied to `<website-dir>/public/modules/cdn_office_suite`. Never distribute `deckcraft-data`, configuration backups or legacy document archives: they can contain private data and credentials.

## Operation and recovery

```sh
systemctl status cdn-office-updater.service
journalctl -u cdn-office-updater.service -n 100 --no-pager
curl http://127.0.0.1:8769/api/status
sudo systemctl restart cdn-office-updater.service
```

The office host and OC4D are enabled at boot. On restart, the host reloads saved jobs and resumes unfinished work. After a hostname/IP change, rerun with the correct `--hosts`. For maintenance that waits on internet, restore the Pi's network; the worker retries automatically. A failed verification keeps the current release and requires a new check/approval. Previous releases and backups consume disk space; no automatic history pruning is implemented.

## Resource use and validation

The shared host uses Python's standard library, streams files and limits concurrent request threads. It requires no extra Python packages or server-side editor build. Short simulations at 5, 10 and 20 clients produced zero office request failures, approximately 24-25 MiB host RSS and 1.8-5.1% of one CPU core during warm traffic. A 20-client cold download burst used about 25.2 MiB RSS and 22.8% of one core. OC4D had occasional multi-second delays. Browser rendering, large projects and sustained real-user workloads can differ; these measurements are not a capacity guarantee. See `deckcraft/CAPACITY.md` and `deckcraft/VERIFICATION.md` for methodology and limits.

```sh
cd deckcraft
python3 -m unittest -v
cd ..
node deckcraft/test_ports.cjs     # custom ports and fail-closed browser configuration
node deckcraft/test_updates.cjs   # optional developer UI simulation; Node is not a runtime requirement
python3 package_installer.py
```

The release checksums, archive safety, authentication, maintenance, rollback, shared update lock, durable jobs, retry behavior and restart recovery are covered by tests. Browser checks include all seven app screens, superadmin release checking and the mobile launcher. Full format compatibility and large-project performance are not exhaustively tested.

## Upstream and licenses

[Wordcraft](https://github.com/storytold/wordcraft), [Gridcraft](https://github.com/storytold/gridcraft), [Deckcraft](https://github.com/storytold/deckcraft), [PDFcraft](https://github.com/storytold/pdfcraft), [Vectorcraft](https://github.com/storytold/vectorcraft), [CADcraft](https://github.com/storytold/cadcraft), [Photocraft](https://github.com/storytold/photocraft). Official icon sources, bundled versions and checksums are recorded in `deckcraft/bundled/releases.json`. See `THIRD_PARTY.md` for attribution and license files.


## Remote access through OC4D Gateway

For gateway hostnames such as `192x168x191x243-3000.52.47.49.176.nip.io`, the launcher encodes each configured backend port in the hostname: Craft uses `192x168x191x243-8769.52.47.49.176.nip.io`, and existing mail uses `192x168x191x243-2000.52.47.49.176.nip.io`. The gateway's public scheme and listening port are retained. Direct LAN addresses still use ordinary explicit port numbers. API requests include gateway cookies when this hostname format is detected.

The gateway must run the matching `gateway-proxy.js` Origin/CORS translation fix from the oc4d-gateway repository. Without it, browser module/WASM requests send a public nip.io Origin while the backend sees a private Host, producing 403. The correction belongs in the gateway; do not disable the office host checks or superadmin authorization. A gateway login may be needed once for the Craft `-8769` hostname before cross-host launcher/admin requests work, since gateway session cookies remain hostname-scoped. OC4D superadmin login is separately required for updates. Restart the gateway after deploying its code and refresh the launcher after updating the Office Suite.
