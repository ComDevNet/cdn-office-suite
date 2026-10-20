"""Install browser apps on an existing OC4D Linux systemd server."""
import argparse
import datetime
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import socket
import subprocess
import time
from urllib.request import urlopen
from configuration import saved_ports, resolve_ports
from bootstrap import prepare
from server import APPS, Manager
from remove_legacy import remove as remove_legacy


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--oc4d-service', default='oc4d.service')
    p.add_argument('--website-dir', type=Path)
    p.add_argument('--install-dir', type=Path)
    p.add_argument('--port', type=int)
    p.add_argument('--oc4d-port', type=int)
    p.add_argument('--mail-port', type=int)
    p.add_argument('--hosts')
    p.add_argument('--online', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if os.name != 'posix' or not Path('/run/systemd/system').exists():
        p.error('Requires Linux, systemd, and an existing OC4D installation')
    if not a.dry_run and os.geteuid() != 0:
        p.error('Run with sudo')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.@-' for c in a.oc4d_service):
        p.error('Invalid service name')
    user = run('systemctl', 'show', a.oc4d_service, '--property=User', '--value')
    if not user or user == 'root':
        p.error('OC4D must use a dedicated non-root service user')
    account = pwd.getpwnam(user)
    website = (a.website_dir or Path(run('systemctl', 'show', a.oc4d_service, '--property=WorkingDirectory', '--value'))).resolve()
    install = (a.install_dir or Path(account.pw_dir) / 'cdn-office-suite').resolve()
    source = Path(__file__).resolve().parent.parent
    data = install / 'deckcraft-data'
    module = website / 'public/modules/cdn_office_suite'
    hosts = a.hosts or ','.join(dict.fromkeys(['localhost', '127.0.0.1', socket.gethostname()] + [ip for ip in run('hostname', '-I').split() if ':' not in ip]))
    if not (website / 'public').is_dir():
        p.error('Use --website-dir to specify the OC4D website directory')
    if str(install) in ('/', '/home', '/usr', '/etc') or any(c.isspace() for c in str(install)):
        p.error('Use a dedicated install directory without whitespace')
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,-' for c in hosts):
        p.error('Use IPv4 addresses or DNS names for --hosts')
    try:
        ports = resolve_ports(saved_ports(data, module), a.port, a.oc4d_port, a.mail_port)
    except (ValueError, OSError, TypeError) as error:
        p.error(str(error))
    a.port, a.oc4d_port, a.mail_port = (ports[key] for key in ('port', 'oc4dPort', 'mailPort'))
    if any(not 1024 <= port <= 65535 for port in (a.port, a.oc4d_port, a.mail_port)) or len({a.port, a.oc4d_port, a.mail_port}) != 3:
        p.error('Use distinct ports between 1024 and 65535')
    print(json.dumps({'website': str(website), 'install': str(install), 'user': user, 'hosts': hosts, 'apps': list(APPS), 'mail': 'keep existing', 'ports': ports}, indent=2))
    if a.dry_run:
        remove_legacy(Path(account.pw_dir), install, website, dry_run=True)
        return
    if shutil.disk_usage(install if install.exists() else install.parent).free < 1024**3:
        p.error('At least 1 GB free disk space is required')
    with socket.socket() as probe:
        if probe.connect_ex(('127.0.0.1', a.port)) == 0:
            pid = run('systemctl', 'show', 'cdn-office-updater.service', '--property=MainPID', '--value')
            listeners = run('ss', '-ltnp', f'sport = :{a.port}')
            if pid in ('', '0') or f'pid={pid},' not in listeners:
                p.error('Office port is occupied by another service')
    install.mkdir(parents=True, exist_ok=True)
    data.mkdir(exist_ok=True)
    auth = data / 'oc4d-auth.env'
    secret = None
    if auth.exists():
        for line in auth.read_text().splitlines():
            if line.startswith('AUTH_SECRET='):
                secret = line.split('=', 1)[1].strip().strip('"').strip("'")
    if not secret:
        pid = run('systemctl', 'show', a.oc4d_service, '--property=MainPID', '--value')
        if pid != '0':
            for item in Path('/proc/' + pid + '/environ').read_bytes().split(b'\0'):
                if item.startswith(b'AUTH_SECRET='):
                    secret = item.split(b'=', 1)[1].decode()
    changed_auth = not secret or len(secret) < 32 or secret == 'default-secret'
    if changed_auth:
        secret = secrets.token_hex(32)
    if any(c in secret for c in '\n\r\0'):
        p.error('Invalid authentication secret')
    bundled = source / 'deckcraft/bundled'
    managers = [Manager(data if app == 'deckcraft' else data / app, app=app) for app in APPS]
    pointers = [(manager, manager.active(), manager.active('previous')) for manager in managers]
    prepare(data, bundled, True)
    backup = install / 'backups' / datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
    backup.mkdir(parents=True)
    runtime = install / 'deckcraft'
    unit = Path('/etc/systemd/system/cdn-office-updater.service')
    dropin = Path('/etc/systemd/system') / (a.oc4d_service + '.d/office-auth.conf')
    tracked = [runtime, module, unit, dropin, auth, data / 'service.env', data / 'installation.json']
    existed = {}
    for i, target in enumerate(tracked):
        existed[target] = target.exists()
        if target.exists():
            if target.is_dir():
                shutil.copytree(target, backup / str(i), ignore=shutil.ignore_patterns('bundled', '__pycache__'))
            else:
                shutil.copy2(target, backup / str(i))
    try:
        runtime.mkdir(exist_ok=True)
        for name in ('server.py', 'configuration.py', 'maintenance.js', 'updates-panel.html'):
            if (source / 'deckcraft' / name).resolve() != (runtime / name).resolve():
                shutil.copy2(source / 'deckcraft' / name, runtime / name)
        (runtime / 'icons').mkdir(exist_ok=True)
        for app in APPS:
            shutil.copy2(source / 'cdn_office_suite/assets/images' / (app + '-icon.png'), runtime / 'icons' / (app + '-icon.png'))
        if (source / 'cdn_office_suite').resolve() != module.resolve():
            shutil.copytree(source / 'cdn_office_suite', module, dirs_exist_ok=True)
        (module / 'settings.js').write_text('window.OFFICE_CONFIG=' + json.dumps(ports) + ';\n')
        (data / 'installation.json').write_text(json.dumps({**ports, 'apps': list(APPS)}, indent=2) + '\n')
        auth.write_text('AUTH_SECRET=' + secret + '\n')
        env = data / 'service.env'
        env.write_text(f'OC4D_BASE_URL=http://127.0.0.1:{a.oc4d_port}\nOFFICE_PORT={a.port}\nOFFICE_MAIL_PORT={a.mail_port}\nOFFICE_ALLOWED_HOSTS={hosts}\n')
        for file in (auth, env):
            file.chmod(0o600)
        for folder in (data, runtime, module):
            for base, dirs, files in os.walk(folder):
                os.chown(base, account.pw_uid, account.pw_gid)
                for name in dirs + files:
                    os.chown(Path(base) / name, account.pw_uid, account.pw_gid, follow_symlinks=False)
        dropin.parent.mkdir(parents=True, exist_ok=True)
        dropin.write_text(f'[Service]\nEnvironmentFile={auth}\n')
        unit.write_text(f'''[Unit]
Description=CDN Office browser apps and protected updates
After=network.target {a.oc4d_service}
[Service]
User={user}
WorkingDirectory={runtime}
EnvironmentFile={auth}
EnvironmentFile={env}
ExecStart=/usr/bin/python3 {runtime}/server.py --root {data} --port {a.port} --mail-port {a.mail_port} --hosts {hosts}
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths={data}
UMask=0077
[Install]
WantedBy=multi-user.target
''')
        run('systemctl', 'daemon-reload')
        run('systemctl', 'enable', 'cdn-office-updater.service', a.oc4d_service)
        run('systemctl', 'restart', 'cdn-office-updater.service')
        run('systemctl', 'restart', a.oc4d_service)
        for attempt in range(60):
            try:
                with urlopen(f'http://127.0.0.1:{a.oc4d_port}/modules/cdn_office_suite/index.html', timeout=3) as response:
                    assert response.status == 200
                for app in APPS:
                    with urlopen(f'http://127.0.0.1:{a.port}/{app}/index.html', timeout=3) as response:
                        assert response.status == 200
                break
            except Exception:
                if attempt == 59:
                    raise
                time.sleep(1)
        print(f'Verified all {len(APPS)} apps; office host starts automatically at boot. Backup:', backup)
        if changed_auth:
            print('Private authentication secret created: existing users must sign out and sign in once.')
    except Exception:
        for manager, current, previous in pointers:
            for name, target in [('current', current), ('previous', previous)]:
                if target:
                    manager.point(name, target)
                else:
                    (manager.root / name).unlink(missing_ok=True)
        for i, target in enumerate(tracked):
            if existed[target]:
                if target.is_dir():
                    shutil.copytree(backup / str(i), target, dirs_exist_ok=True)
                else:
                    shutil.copy2(backup / str(i), target)
            elif target.is_file():
                target.unlink()
        run('systemctl', 'daemon-reload')
        subprocess.run(['systemctl', 'restart', 'cdn-office-updater.service'])
        subprocess.run(['systemctl', 'restart', a.oc4d_service])
        raise
    # Remove legacy tools only after replacement health checks succeed.
    remove_legacy(Path(account.pw_dir), install, website)


if __name__ == '__main__':
    main()
