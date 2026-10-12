"""Build a portable offline installer without server data or credentials."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

root = Path(__file__).resolve().parent
manifest = json.loads((root / 'deckcraft/bundled/releases.json').read_text())
expected_apps = {'deckcraft', 'wordcraft', 'gridcraft', 'pdfcraft', 'vectorcraft', 'cadcraft', 'photocraft'}
if set(manifest) != expected_apps:
    raise ValueError('Installer must contain all seven Craft applications')
files = ['install.sh', 'README.md', 'deckcraft/README.md', 'cdn_office_suite/README.md', 'citadel/readme.md', 'THIRD_PARTY.md', 'third_party/LICENSE-MIT', 'third_party/LICENSE-APACHE',
         'deckcraft/configuration.py', 'deckcraft/server.py', 'deckcraft/bootstrap.py', 'deckcraft/install_suite.py',
         'deckcraft/test_configuration.py', 'deckcraft/test_ports.cjs', 'deckcraft/test_favicons.py', 'deckcraft/test_updates.cjs', 'deckcraft/test_jobs.py', 'deckcraft/test_server.py', 'deckcraft/test_legacy.py', 'deckcraft/remove_legacy.py', 'deckcraft/maintenance.js', 'deckcraft/updates-panel.html',
         'deckcraft/VERIFICATION.md', 'deckcraft/CAPACITY.md', 'deckcraft/bundled/releases.json',
         'cdn_office_suite/index.html', 'cdn_office_suite/updates.html',
         'cdn_office_suite/office.css', 'cdn_office_suite/settings.js', 'cdn_office_suite/connection.js', 'cdn_office_suite/favicon.ico']
for app, release in manifest.items():
    path = root / 'deckcraft/bundled' / release['name']
    if hashlib.sha256(path.read_bytes()).hexdigest() != release['sha256']:
        raise ValueError('Bundled checksum mismatch: ' + app)
    icon = root / ('cdn_office_suite/assets/images/' + app + '-icon.png')
    if hashlib.sha256(icon.read_bytes()).hexdigest() != release['icon_sha256']:
        raise ValueError('Official icon checksum mismatch: ' + app)
    files += ['deckcraft/bundled/' + release['name'], 'deckcraft/bundled/' + app + '-SHA256SUMS.txt']
for name in ['cdn-logo-transparent.webp', 'untitled-3.webp', *[app+'-icon.png' for app in manifest]]:
    files.append('cdn_office_suite/assets/images/' + name)
output = root / 'dist/cdn-office-suite-installer-v0.9.0.tar.gz'
output.parent.mkdir(exist_ok=True)
with output.open('wb') as raw, gzip.GzipFile(fileobj=raw, mode='wb', mtime=0) as compressed, tarfile.open(fileobj=compressed, mode='w') as archive:
    for name in files:
        content = (root / name).read_bytes()
        if Path(name).suffix in {'.py', '.sh', '.js', '.html', '.css', '.md'}:
            content = content.replace(b'\r\n', b'\n')
        info = tarfile.TarInfo('cdn-office-suite-installer/' + name)
        info.size = len(content)
        info.mode = 0o755 if name.endswith('.sh') else 0o644
        archive.addfile(info, io.BytesIO(content))
digest = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix(output.suffix + '.sha256').write_text(digest + '  ' + output.name + '\n')
print(output, output.stat().st_size, digest)

