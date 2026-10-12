# Shared host for all seven Craft apps

This directory serves **Wordcraft, Gridcraft, Deckcraft, PDFcraft, Vectorcraft, CADcraft and Photocraft**. Its historical name is `deckcraft`; separate app source folders are not required. The installer unpacks each official WebAssembly release into versioned storage on the destination server. Mail uses the server's existing installation.

Use the [root README](../README.md) for the complete app list, prerequisites, installation/upgrade commands, configuration, repository and server layouts, private data handling, update behavior, resource measurements and limitations. Run the root `install.sh`; the `install.sh` here delegates to it for compatibility.

## Files

- `server.py` serves app assets and official favicons, verifies superadmin access, checks releases, saves update jobs, retries temporary outages, switches active releases and offers rollback.
- `bootstrap.py` stages and validates bundled or online releases for all seven apps.
- `install_suite.py` integrates the host and launcher with an existing OC4D systemd installation, enables boot startup and verifies app health.
- `remove_legacy.py` removes recognized retired Etherpad/Ethercalc installations after privately archiving documents. It refuses unfamiliar packages and symlinks.
- `maintenance.js` blocks affected app tabs during queued updates, installation and retry waiting.
- `updates-panel.html` contains administrator controls; the host returns it only after server-side authorization.
- `bundled/releases.json` records versions, official release/icon sources and checksums. Release ZIPs are included in the portable archive, not committed to Git.
- `test_server.py`, `test_jobs.py`, `test_legacy.py`, `test_favicons.py` cover release safety, access, maintenance, rollback, cleanup, disconnected clients, retry and restart recovery.
- `test_updates.cjs` checks the update UI's progress retention and recovery using Node without browser or server changes.
- `VERIFICATION.md` records deployment and testing; `CAPACITY.md` explains resource simulations and their limits.

## Update behavior

A superadmin checks and approves one specific release. The host saves approval before returning, runs independently of the browser, persists progress and recovers unfinished jobs after service restarts. Network/download failures retry with backoff. Reconnecting clients retrieve saved progress. Interrupted downloads restart; checksum failures or changed release files stop for review. One app updates at a time; only the affected app is in maintenance. The previous release remains available for approved rollback.

## Developer checks

Run `python3 -m unittest -v` from this directory on Linux. Run `node deckcraft/test_updates.cjs` from the repository root for the optional UI simulation. Production needs Python 3.10+, systemd and iproute2; no Node, Rust toolchain or third-party Python modules are needed. Use `python3 package_installer.py` from the root to build the offline distribution.

## Fixed ports and complete installation

`configuration.py` validates and preserves office, OC4D and mail ports in `deckcraft-data/installation.json`. Installer reruns reuse them unless a port flag explicitly changes one. The host requires explicit ports, checks them against the saved configuration and stops if its port is occupied, instead of trying another. All seven tools share the office port and have separate app routes. The launcher and Updates page validate their generated settings using `connection.js`; invalid settings stop requests. Mail readiness uses the actual configured mail port.

The installer and package builder require the complete seven-app registry. A fresh offline installation is covered by a test that verifies every app's active release and WebAssembly assets. `test_configuration.py` covers retained/custom ports, migration, invalid/colliding settings, occupied ports and runtime mismatch. `test_ports.cjs` covers explicit browser endpoints and invalid configuration. Mail remains the existing server setup.
