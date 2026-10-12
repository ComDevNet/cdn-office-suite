"""Remove recognized Etherpad/Ethercalc installs, retaining a private data archive."""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile


def recognized(path, names):
    try:
        return json.loads((path / 'package.json').read_text()).get('name') in names
    except (OSError, ValueError):
        return False


def remove(home, install, website, dry_run=False):
    home, install, website = home.resolve(), install.resolve(), website.resolve()
    units = []
    for name in ('etherpad.service', 'etherpad-lite.service', 'ethercalc.service'):
        unit = Path('/etc/systemd/system') / name
        if unit.exists():
            text = unit.read_text().lower()
            if 'etherpad' not in text and 'ethercalc' not in text:
                raise ValueError('Refusing to remove unrecognized unit: ' + str(unit))
            units.append(unit)
    folders = []
    for path in [home / 'etherpad-lite', home / 'etherpad', Path('/opt/etherpad-lite'), Path('/opt/etherpad')]:
        if path.exists():
            if path.is_symlink() or not recognized(path, {'etherpad', 'etherpad-lite', 'ep_etherpad-lite'}):
                raise ValueError('Unrecognized Etherpad install: ' + str(path))
            folders.append(path)
    modules = [Path('/usr/local/lib/node_modules/ethercalc'), Path('/usr/lib/node_modules/ethercalc')]
    modules += list((home / '.nvm/versions/node').glob('*/lib/node_modules/ethercalc'))
    for path in modules:
        if path.exists():
            if path.is_symlink() or not recognized(path, {'ethercalc'}):
                raise ValueError('Unrecognized Ethercalc package: ' + str(path))
            folders.append(path)
    assets = []
    for base in [install, home / 'office-suite-installer']:
        for name in ('etherpad-lite', 'ethercalc'):
            path = base / name
            if path.is_dir() and not path.is_symlink() and (path / ('word_install.sh' if name == 'etherpad-lite' else 'spreadsheet_install.sh')).is_file():
                folders.append(path)
    for base in [install / 'cdn_office_suite', home / 'office-suite-installer/cdn_office_suite', website / 'public/modules/cdn_office_suite']:
        for name in ('etherpad_not_installed.html', 'ethercalc_not_installed.html'):
            if (base / name).is_file():
                assets.append(base / name)
        for name in ('citadel_not_installed.html', 'script.js'):
            obsolete = base / name
            if obsolete.is_file() and not obsolete.is_symlink():
                text = obsolete.read_text(errors='replace')
                if ('Etherpad' in text and 'Ethercalc' in text) or ('serviceFileName' in text and '_not_installed.html' in text):
                    assets.append(obsolete)
        project = base / 'project.mobirise'
        if project.is_file() and not project.is_symlink():
            old = project.read_text(errors='replace').lower()
            if 'etherpad' in old and 'ethercalc' in old:
                assets.append(project)
    links = []
    for module in modules:
        binary = module.parents[2] / 'bin/ethercalc'
        if binary.is_symlink() and module.resolve() in binary.resolve().parents:
            links.append(binary)
    dumpfiles = []
    has_calc = any(unit.name == 'ethercalc.service' for unit in units) or any(module in folders for module in modules)
    has_pad = any('etherpad' in unit.name for unit in units) or any(recognized(folder, {'etherpad', 'etherpad-lite', 'ep_etherpad-lite'}) for folder in folders)
    for folder in ([Path('/dump'), home / 'dump'] if has_calc else []):
        for file in list(folder.glob('snapshot-*.txt')) + list(folder.glob('audit-*.txt')):
            if file.is_file() and not file.is_symlink():
                dumpfiles.append(file)
    logs = [path for path in [Path('/var/log/etherpad'), Path('/var/log/ethercalc')] if path.is_dir() and not path.is_symlink()]
    datafiles = list(dumpfiles)
    for folder in folders:
        if folder.name.startswith('etherpad'):
            datafiles += [p for p in (folder / 'var').rglob('*') if p.is_file() and not p.is_symlink() and
                          (p.suffix in {'.db', '.sqlite', '.sqlite3'} or any(p.name.endswith(s) for s in ('.db-wal', '.db-shm', '.db-journal')))]
            datafiles += [folder / name for name in ('settings.json', 'credentials.json') if (folder / name).is_file()]
    plan = {'units': [str(p) for p in units], 'folders': [str(p) for p in dict.fromkeys(folders + logs)],
            'files': [str(p) for p in assets + links + dumpfiles], 'data_files_to_archive': len(datafiles)}
    print(json.dumps(plan, indent=2), flush=True)
    if dry_run:
        return plan
    if os.geteuid() != 0:
        raise PermissionError('Run cleanup with sudo')
    abiword_packages = []
    for name in ('abiword', 'abiword-common', 'libabiword-3.0', 'abiword-plugin-grammar', 'abiword-plugin-collab'):
        package = subprocess.run(['dpkg-query', '-W', '-f=${Status}', name], capture_output=True, text=True)
        if has_pad and package.stdout.strip() == 'install ok installed':
            abiword_packages.append(name)
    if abiword_packages:
        simulation = subprocess.run(['apt-get', '-s', 'purge', *abiword_packages], check=True, capture_output=True, text=True)
        removals = [line.split()[1] for line in simulation.stdout.splitlines() if line.startswith(('Remv ', 'Purg '))]
        if any(not (name in {'abiword', 'abiword-common'} or name.startswith(('abiword-plugin-', 'libabiword-'))) for name in removals):
            raise ValueError('Abiword is required by another installed package; remove it separately after checking that dependency')
    for unit in units:
        subprocess.run(['systemctl', 'disable', '--now', unit.name], check=True)
    if datafiles:
        backup = install / 'legacy-data-backups'
        backup.mkdir(mode=0o700, exist_ok=True)
        backup.chmod(0o700)
        archive = backup / ('documents-' + datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f') + '.tar.gz')
        try:
            with tarfile.open(archive, 'w:gz') as output:
                for file in dict.fromkeys(datafiles):
                    output.add(file, arcname=str(file).lstrip('/'), recursive=False)
            archive.chmod(0o600)
            with tarfile.open(archive) as verify:
                for member in verify.getmembers():
                    source = verify.extractfile(member)
                    if source:
                        while source.read(1024 * 1024):
                            pass
            print('Private document archive:', archive, flush=True)
        except Exception:
            for unit in units:
                subprocess.run(['systemctl', 'enable', '--now', unit.name])
            raise
    for file in units + links + assets + dumpfiles:
        file.unlink(missing_ok=True)
    for folder in dict.fromkeys(folders + logs):
        if folder.exists():
            shutil.rmtree(folder)
    for folder in {p.parent for p in dumpfiles}:
        if folder.exists() and not any(folder.iterdir()):
            folder.rmdir()
    subprocess.run(['systemctl', 'daemon-reload'], check=True)
    if abiword_packages:
        subprocess.run(['apt-get', '-y', 'purge', *abiword_packages], check=True)
    subprocess.run(['systemctl', 'reset-failed', 'etherpad.service', 'etherpad-lite.service', 'ethercalc.service'], stderr=subprocess.DEVNULL)
    print('Legacy software removed. Mail, shared Node/Python runtimes and databases were not removed.', flush=True)
    return plan


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, required=True)
    p.add_argument('--install-dir', type=Path, required=True)
    p.add_argument('--website-dir', type=Path, required=True)
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    remove(a.home, a.install_dir, a.website_dir, a.dry_run)
