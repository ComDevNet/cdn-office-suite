"""Prepare verified web releases without changing systemd or existing documents."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import secrets
import shutil
import time

from server import APPS, Manager, latest_release, unpack_release, version


def prepare(root, bundled, online=False):
    root.mkdir(parents=True, exist_ok=True)
    marker = root / ".installer-maintenance"
    with (root / "operations.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        releases = json.loads((bundled / "releases.json").read_text()) if not online else {}
        stages = []
        temp_stages = []
        switched = []
        try:
            # Stage all downloads before changing any active pointer.
            for app in APPS:
                manager = Manager(root if app == "deckcraft" else root / app, app=app)
                release = latest_release(app) if online else releases[app]
                expected_name = app + "-web-" + release["version"].removeprefix("v") + ".zip"
                if release.get("app", app) != app or release["name"] != expected_name:
                    raise ValueError("Invalid bundled release metadata")
                release = {**release, "app": app}
                installed = manager.installed()
                active = manager.active()
                if installed and version(installed) >= version(release["version"]):
                    if not (active / "index.html").is_file() or not list(active.rglob("*.wasm")) or not list(active.rglob("*.js")):
                        raise ValueError(f"{app} has an incomplete existing release; restore it before reinstalling")
                    print(app, installed, "already installed", flush=True)
                    continue
                for stale in manager.releases.glob(".staging-*"):
                    if stale.is_dir() and not stale.is_symlink():
                        shutil.rmtree(stale)
                verified = manager.releases / (".verified-" + release["version"])
                if online and verified.is_dir() and (verified / "cdn-release.json").is_file() and (verified / "index.html").is_file() and list(verified.rglob("*.wasm.gz")) and list(verified.rglob("*.js.gz")):
                    stages.append((manager, release, verified))
                    print("Prepared", app, release["version"], "(cached)", flush=True)
                    continue
                stage = manager.releases / (".staging-" + secrets.token_hex(6))
                stage.mkdir()
                temp_stages.append(stage)
                print("Preparing", app, release["version"], flush=True)
                last_bucket = -1
                def report(step, _percent, downloaded=None, total=None):
                    nonlocal last_bucket
                    if step == "download" and downloaded is not None and total:
                        bucket = int(downloaded * 5 // total)
                        if bucket > last_bucket and bucket > 0:
                            last_bucket = bucket
                            print(f"  {app}: {min(100, bucket * 20)}% ({downloaded / 1048576:.1f} / {total / 1048576:.1f} MB)", flush=True)
                unpack_release(release, stage, None if online else bundled, progress=report if online else None)
                if online:
                    if verified.exists():
                        shutil.rmtree(verified)
                    stage.rename(verified)
                    stages.append((manager, release, verified))
                else:
                    stages.append((manager, release, stage))
            if stages:
                marker.write_text(json.dumps({"pid": os.getpid(), "start": Path(f"/proc/{os.getpid()}/stat").read_text().split()[21]}))
                time.sleep(2)
                for manager, release, stage in stages:
                    destination = manager.releases / release["version"]
                    if destination.exists():
                        # Never overwrite a retained release with different files.
                        destination = manager.releases / (release["version"] + "-" + secrets.token_hex(4))
                    stage.rename(destination)
                    old = manager.active()
                    previous = (manager.root / 'previous').resolve() if (manager.root / 'previous').exists() else None
                    switched.append((manager, old, previous))
                    if old:
                        manager.point("previous", old)
                    manager.point("current", destination)
                    print("Installed", manager.app, manager.installed(), flush=True)
        except Exception:
            for manager, old, previous in reversed(switched):
                for name, target in [('current', old), ('previous', previous)]:
                    if target:
                        manager.point(name, target)
                    else:
                        (manager.root / name).unlink(missing_ok=True)
            raise
        finally:
            marker.unlink(missing_ok=True)
            for stage in temp_stages:
                if stage.exists():
                    shutil.rmtree(stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--bundle-dir", type=Path, default=Path(__file__).parent / "bundled")
    parser.add_argument("--online", action="store_true")
    args = parser.parse_args()
    prepare(args.data_dir.resolve(), args.bundle_dir.resolve(), args.online)
