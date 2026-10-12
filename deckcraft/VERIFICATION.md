# Live verification: three Craft apps (2026-10-12)

Target: Raspberry Pi 4, ARM64 Debian 12, 4 GB RAM, existing OC4D systemd installation.

- Wordcraft, Gridcraft, Deckcraft: checksum-verified v0.5.0 releases installed. Mail untouched; old Etherpad/Ethercalc services and software removed in the subsequent cleanup. Documents retained only in a private archive.
- Actual installer ran successfully on the Pi, then ran again without replacing installed releases. Fresh storage at /tmp/office-fresh-test installed all three bundled archives and a repeated bootstrap skipped all three.
- Office host and OC4D are enabled at boot. Service restarts and all three index endpoints passed installer health checks.
- Seventeen Linux host/cleanup tests passed: archive verification, gzip, unsafe paths, short downloads, checksum failure, preserved active release on failure, approval freshness, update/rollback, signed-session/database-role checks, app-specific archives, shared update lock, and failed bootstrap checksum/pointer activation recovery.
- Anonymous update requests for all three apps returned 401. Signed-in OC4D superadmin controls displayed all three installed versions and a real Wordcraft release check returned latest v0.5.0. Public Updates page showed sign-in guidance without controls.
- Browser smoke checks: Wordcraft rendered and accepted a sentence; Gridcraft rendered and accepted numeric cell data; Deckcraft rendered in the earlier deployment. Launcher renders with official icons, no sidebar, keyboard focus and phone layout. Widths 390 and 320 showed no horizontal overflow.
- JavaScript syntax checks passed for launcher, Updates page and maintenance script. git diff --check passed.
- With eight simultaneous compressed WASM downloads, all responses were 200/gzip. Host RSS baseline 22,832 KiB; sampled peak 24,156 KiB. Available Pi memory approximately 2.8 GB. This measures file serving, not a full multi-user endurance benchmark or client browser memory.
- Isolated host using actual releases: Wordcraft maintenance returned 503 while Deckcraft and Gridcraft returned 200. Live service and user content were not altered for this fixture.

Limits: apps remain upstream alpha software. Save actions were exercised in the in-app browser, but its download event API did not report a file; exported-document contents have not been verified. Test saving and reopening a real file in the browser you intend to use before relying on the apps. No second physical server was available; full installer was verified on this Pi and clean release storage, not every Linux environment. Modern WebGL2/WebGPU-capable clients are required.

Backups: /home/pi/cdn-office-suite/backups/20261011T235209543468 and /home/pi/cdn-office-suite/backups/20261011T235554018735. Server credentials are excluded from the distribution archive.


## Legacy removal and capacity tests — 12 October 2026

Etherpad and Ethercalc units, application files, global binary, legacy scripts, fallback pages and logs were removed. Ports 9001/8000 are closed. Abiword, its grammar plugin, common files and core library were purged without a broad autoremove. Shared runtimes, mail and databases remain. Document data was privately archived in /home/pi/cdn-office-suite/legacy-data-backups/documents-20261012T001326124387.tar.gz (332,466 bytes, mode 0600).

The root installer now invokes safe, recognized legacy removal after replacement health checks. All 17 tests passed, including 3 identity/symlink cleanup tests. Actual cleanup, repeat cleanup and a complete installer rerun passed on the Pi. Office/OC4D services remain active and enabled at boot.

External steady-use simulations: 5 / 10 / 20 users, 25 seconds each, 90 / 202 / 400 office requests with zero failures. Office p95 latency: 223 / 213 / 257 ms. Host peak RSS: 23.86 / 23.99 / 24.49 MiB. Average host CPU: 1.81 / 3.49 / 5.14 percent of one core. No swap growth; minimum available Pi memory about 1.8 GiB. OC4D categories checks succeeded but had occasional p95 delays up to 5.9 seconds; their cause was not isolated.

Pi-local simultaneous compressed WASM downloads at 5 / 10 / 20 clients also had zero failures. Peak host RSS reached 25.24 MiB; the 20-client burst served 213.6 MiB in 3.47 seconds at 22.79 percent of one core. This loopback stress excludes real Wi-Fi and browser rendering. These are short server workload simulations, not a 20-person endurance or client project benchmark.

Full methodology, per-app assessment and source links are in deckcraft/CAPACITY.md; raw results are in dist/office-load-test.json and dist/office-cold-load-before.json. The additional seven apps were assessed, not installed.

## Four additional apps installed — 12 October 2026

Checksum-verified official releases installed: PDFcraft v0.6.0, Vectorcraft v0.9.0, CADcraft v0.5.0 and Photocraft v0.7.0. All original app versions remain unchanged. The host now serves all seven Craft apps, and all seven have signed OC4D superadmin update controls with approval, maintenance blocking and rollback. Official icons were added to the launcher and distribution.

The full installer ran successfully using the seven bundled releases. Health checks passed for all seven editors; office and OC4D services are active and enabled at boot. All 17 Linux tests passed again, including archive validation and shared update locks across the expanded app registry. Anonymous update checks for each new app returned 401. Vectorcraft’s 15-character asset hash is recognized for immutable caching; a real asset response verified that header.

Browser checks: all four new interfaces rendered over the Pi’s existing HTTP service. Vectorcraft and Photocraft created new documents, CADcraft drew a line, and PDFcraft reached its ready tools interface. The signed-in superadmin tab listed all seven installed versions and checked PDFcraft against its real upstream latest release. Mobile launcher at 390 px showed eight tool cards and no horizontal overflow. JS syntax checks and git diff --check passed. Import/export workflows and large-project rendering were not exhaustively tested.

The updated offline installer artifact is cdn-office-suite-installer-v0.6.0.tar.gz; this is the installer revision, while each application retains its own version. Mail remains the existing Citadel service. Legacy services remain removed and their private document archive is retained.


## Durable update jobs and playful UI - 12 October 2026

Deployed server.py, the protected update panel and launcher styles on the Pi. The office service restarted successfully and is active/enabled at boot. All seven installed versions remain unchanged. Runtime and launcher backup: /home/pi/cdn-office-suite/backups/durable-jobs-1791767607.

All 24 Linux tests passed on the Pi. Added coverage for a disconnected HTTP client, persisted progress, temporary internet failure and automatic retry, service restart recovery, recovery in a fresh Python process, interruption after activation, and checksum/changed-release rejection. Fixtures use temporary release storage; no production download outage or Pi reboot was induced. Frontend simulation verifies retained progress during disconnect, retry/completion after reconnect and rejection of stale status. JavaScript syntax checks and git diff --check passed.

The live signed-in superadmin panel loads all seven installed versions. Anonymous mutation is rejected. UI changes use existing official icons, larger artwork, soft offset shadows, a drawn title underline and subtle hover motion with reduced-motion support. Progress shows the current stage, percentage, download size and retry state. Jobs run on the server, persist before acceptance and resume after host restarts. Temporary network failures retry the exact approved release with backoff; interrupted downloads restart, rather than resuming byte ranges. Invalid checksums or changed release metadata require review instead of retrying.

Installer revision v0.7.0 includes the same durable job backend and UI, seven checksum-verified app releases and the added tests. Existing mail configuration and superadmin authentication remain in place.


## Repository cleanup, complete documentation and favicons - 12 October 2026

Removed the local Etherpad/Ethercalc installer folders, service templates, settings and READMEs. Removed the retired fallback pages, legacy launcher script and old Mobirise project. The safe installer cleanup also recognizes and removes those obsolete launcher files on existing servers. References that remain in documentation and remove_legacy.py explain migration and private document retention; they do not install the retired applications.

Rewrote all remaining READMEs and added launcher documentation. The root README covers all seven apps, browser-local files, installer prerequisites/options, offline releases, server layouts, superadmin approval, durable updates/retries, maintenance, rollback, boot startup, mail preservation, private storage, operation/recovery, resource measurements, test coverage and limitations. The shared host README now correctly lists seven apps rather than three.

The host injects each app's official PNG favicon into its served HTML and serves it from /APP/favicon.png. Existing upstream icon links are replaced. Favicon files remain reachable during maintenance and are not immutably cached. The installer copies all seven icons into the runtime. Upstream archive contents and checksum identity remain unchanged.

All 25 Linux tests passed, including a new HTTP test across all seven app pages and icons during maintenance. The full root installer reran successfully on the Pi with unchanged app versions and existing mail. Live checks verified HTML favicon links, image/png responses and exact official icon bytes for all seven tools. Obsolete files are absent from runtime, installer source and OC4D public module; private legacy document backups remain. Office and OC4D services are active and enabled. Backup: /home/pi/cdn-office-suite/backups/20261012T012737489228. Frontend reconnect simulation and git diff --check passed. Portable installer revision: v0.8.0.


## Persistent ports and complete installer - 12 October 2026

Saved the explicit office, OC4D and mail ports in deckcraft-data/installation.json with all seven Craft apps. Installer reruns retain omitted port settings; older installations migrate their existing launcher/service settings. Invalid, duplicate or missing existing settings stop the installer. The host requires explicit listening/mail ports and matching saved configuration. Occupied ports stop startup rather than triggering another bind. OC4D identity checks use the explicit local service URL; mail readiness uses its actual configured port. Browser connections validate all three settings, retain an immutable copy and do not guess or reuse the launcher port when configuration is invalid.

All 32 Linux tests passed, including retained/custom port settings, migration, invalid/colliding settings, occupied-port startup failure, runtime configuration mismatch, configured mail readiness and a fresh offline installation of every Craft app. Node port tests verify custom endpoints and fail-closed invalid configuration; reconnect UI tests also passed. The package builder validates the complete seven-app registry and each official icon checksum in addition to release checksums.

The full installer ran successfully on the Pi with no port flags, retaining office 8769, OC4D 3000 and mail 2000. A subsequent dry run retained the saved settings. Runtime systemd arguments match the record. All seven live editor pages and their local assets use 8769; the browser launcher shows all seven app links on 8769 and mail on 2000. The existing mail service is reachable and unchanged. Installer backup: /home/pi/cdn-office-suite/backups/20261012T064311922986. Portable installer revision: v0.9.0. These protections cover configuration and host-generated connections; they do not prevent someone deliberately editing server files or manually navigating their browser elsewhere.


## OC4D Gateway compatibility - 12 October 2026

Reproduced the reported backend 403 on node 192.168.191.243: Photocraft's JS loads without Origin but is rejected with the public gateway Origin. The gateway changes Host through changeOrigin but previously kept Origin public. The oc4d-gateway correction translates same-node/same-gateway Origins into their corresponding backend port, restores accepted CORS origins to public browser origins, uses v3 proxy events and supports safe API preflights while retaining actual-resource session checks and office superadmin authorization.

Updated connection.js to encode destination ports in gateway hostnames while retaining the public gateway scheme/port. Browser API requests include gateway credentials only in gateway mode. Node tests cover HTTP/HTTPS and custom ports, along with unchanged direct-LAN behavior and invalid-config protection. Gateway regression tests passed using a real local HTTP proxy against a loopback backend. A local corrected proxy also retrieved the real Photocraft JS (171,589 bytes) and WASM (24,996,331 bytes) from node .243 with HTTP 200 and correct public CORS origin. The public gateway has not been deployed; its operator must deploy server.js/gateway-proxy.js and restart PM2. Office installer revision: v0.10.0. Existing runtime backend origin/role checks are unchanged.
