# Raspberry Pi office capacity — 12 October 2026

Etherpad and Ethercalc were removed: services, application folders, global binary, legacy installer fragments, fallback pages and logs. Their ports 9001 and 8000 are closed. Abiword and its specific core/plugin packages were purged; shared runtimes, mail and databases remain. Document data is preserved in a root-only archive at /home/pi/cdn-office-suite/legacy-data-backups/documents-20261012T001326124387.tar.gz (332,466 bytes; mode 0600).

The installer now performs recognized legacy cleanup only after replacement health checks pass. It rejects unrecognized package identities and symlinked installs, archives data before deleting files, simulates the Abiword package purge to reject unrelated removals, and leaves existing mail intact. Seventeen tests passed on the Pi, including three cleanup safety tests. The complete installer ran successfully again after cleanup, confirming the operation is repeatable.

## Simulated office use

An external Windows client simulated 5, 10 and 20 users, for 25 seconds each. Each user fetched launcher/editor HTML, polled the app maintenance endpoint every 1.5 seconds and suite status every 10 seconds. Assets are assumed cached for this steady-use test. Editing occurs in the browser; this does not emulate client rendering or office file exports. Pi /proc samples were collected every 0.5 seconds and aligned by start-time offset because the two clocks differ. Office CPU is a percentage of one CPU core (100% = one fully occupied core), while system CPU averages across all four cores.

- 5 users: 90 office requests, 0 failures; p95 223.4 ms; average office CPU 1.81% of one core; peak office memory 23.86 MiB; minimum available Pi memory 1828 MiB.
- 10 users: 202 office requests, 0 failures; p95 213.2 ms; average office CPU 3.49% of one core; peak office memory 23.99 MiB; minimum available Pi memory 2429 MiB.
- 20 users: 400 office requests, 0 failures; p95 256.6 ms; average office CPU 5.14% of one core; peak office memory 24.49 MiB; minimum available Pi memory 1829 MiB.

There was no swap growth during these profiles. OC4D category-page checks all succeeded, but p95 was about 5.9 seconds at 5 users, 0.2 seconds at 10 and 5.1 seconds at 20. This does not demonstrate a monotonic office-load effect; Next.js/database/background/network latency was not isolated. The office host remained small, while the existing OC4D page showed occasional slow responses.

## Cold app-opening bursts

A separate Pi-local stress generator opened compressed WASM downloads simultaneously, reading 64 KiB then waiting 10 ms (approximately 6 MiB/s per user). This checks server file-serving behaviour and excludes real Wi-Fi bandwidth, client startup compilation and rendering. The generator itself ran on the Pi; office process CPU was measured separately.

- 5 downloads: 0 failures; 52.6 MiB served in 2.4 seconds; peak host memory 24.49 MiB; average host CPU 5.83% of one core.
- 10 downloads: 0 failures; 111.1 MiB served in 2.42 seconds; peak host memory 24.61 MiB; average host CPU 12.79% of one core.
- 20 downloads: 0 failures; 213.6 MiB served in 3.47 seconds; peak host memory 25.24 MiB; average host CPU 22.79% of one core.

These short simulations support use by a few people and showed no office failures at 20 simulated users. They are not a 20-person endurance test or a guarantee about the wireless network, every device, file format or upstream alpha application. All three office releases remain v0.5.0.

## Additional apps

All seven publish static web releases and Linux ARM64 packages. Static web hosting does not need native Pi execution or server-side rendering. Browser processing uses the user's device. Current release downloads total approximately 89 MiB compressed ZIPs; installed/retained footprint was not measured. The Pi has approximately 38 GiB free disk space, so storage appears sufficient. This is a hosting feasibility assessment; these seven apps were not installed or benchmarked with real project workloads.

- [Soundcraft v0.5.0](https://github.com/storytold/soundcraft/releases/tag/v0.5.0): web ZIP 4.6 MiB. Pi web hosting is feasible; Limited web file services and demo/empty session; validate recording/import/save needs first.
- [Cadcraft v0.5.0](https://github.com/storytold/cadcraft/releases/tag/v0.5.0): web ZIP 5.5 MiB. Pi web hosting is feasible; Suitable to trial for small drawings; complex models use client CPU/GPU.
- [Pdfcraft v0.6.0](https://github.com/storytold/pdfcraft/releases/tag/v0.6.0): web ZIP 15.8 MiB. Pi web hosting is feasible; Suitable to trial for document reading/editing; large PDFs use client memory.
- [Photocraft v0.7.0](https://github.com/storytold/photocraft/releases/tag/v0.7.0): web ZIP 10.5 MiB. Pi web hosting is feasible; Suitable to trial for modest images; many layers and large images use client memory/GPU.
- [Vectorcraft v0.9.0](https://github.com/storytold/vectorcraft/releases/tag/v0.9.0): web ZIP 20.4 MiB. Pi web hosting is feasible; Suitable to trial for illustration; complex paths and effects use client CPU/GPU.
- [Filmcraft v0.6.0](https://github.com/storytold/filmcraft/releases/tag/v0.6.0): web ZIP 14.9 MiB. Pi web hosting is feasible; Heavy client workload. Current browser build is single-threaded; some desktop commands unavailable. HTTPS enables WebGPU.
- [Effectcraft v0.8.0](https://github.com/storytold/effectcraft/releases/tag/v0.8.0): web ZIP 17.5 MiB. Pi web hosting is feasible; Heavy client workload. WebGPU and offline service-worker features need HTTPS; browser workers can increase client memory.

The current shared host allows only Wordcraft, Gridcraft and Deckcraft, so supporting the seven additional apps requires deliberate routing/update integration. Filmcraft/Effectcraft use different asset naming and need suitable cache rules. For video/VFX, use trusted HTTPS on a server hostname so users can use WebGPU; do not rely on plain HTTP CPU fallback for heavy work. Native rendering/editing on the same 4 GB Pi serving OC4D was not tested and is not the deployment approach recommended here.

Primary technical sources:

- https://github.com/storytold/soundcraft/blob/v0.5.0/apps/soundcraft-web/src/main.rs
- https://github.com/storytold/cadcraft/blob/v0.5.0/apps/cadcraft-web/src/main.rs
- https://github.com/storytold/pdfcraft/blob/v0.6.0/apps/pdfcraft-web/src/main.rs
- https://github.com/storytold/photocraft/blob/v0.7.0/apps/photocraft-web/src/main.rs
- https://github.com/storytold/vectorcraft/blob/v0.9.0/apps/vectorcraft-web/src/main.rs
- https://github.com/storytold/filmcraft/blob/v0.6.0/docs/web.md
- https://github.com/storytold/filmcraft/blob/v0.6.0/packaging/web/README.md
- https://github.com/storytold/effectcraft/blob/v0.8.0/docs/web.md
- https://github.com/storytold/effectcraft/blob/v0.8.0/packaging/web/README.md

Raw evidence: office-load-test.json, office-cold-load-before.json and craft-feasibility-sources.json in dist/. No credentials or document contents are included in these reports.

## Subsequent installation

PDFcraft v0.6.0, Vectorcraft v0.9.0, CADcraft v0.5.0 and Photocraft v0.7.0 were subsequently installed on 12 October 2026. The measurements above describe the earlier three-app deployment; no new twenty-user endurance test was performed for the seven-app deployment. See VERIFICATION.md for current installation and browser checks.
