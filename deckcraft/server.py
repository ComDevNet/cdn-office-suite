"""Static Deckcraft hosting and an approval-gated release updater. Standard library only."""
import argparse
import gzip
import hashlib
import hmac
import io
import json
import logging
import mimetypes
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import socket
import stat
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse
from urllib.request import Request, urlopen
import zipfile
from urllib.error import HTTPError
from urllib.error import URLError
from http.client import IncompleteRead
import errno
from configuration import validate_ports


class AccessDenied(Exception):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


def superadmin(authorization):
    match = re.fullmatch(r"Bearer (.{1,2048})", authorization or "")
    secret = os.environ.get("AUTH_SECRET", "")
    if len(secret) < 32 or secret in {"default-secret", "undefined"}:
        raise AccessDenied(503, "OC4D authentication is not configured")
    if not match:
        raise AccessDenied(401, "Sign in to OC4D to access software updates")
    token = match[1]
    parts = token.rsplit(":", 2)
    if len(parts) != 3 or not parts[1].isdigit() or not re.fullmatch(r"[a-f0-9]{64}", parts[2]):
        raise AccessDenied(401, "Sign in again using this server's OC4D login")
    email, stamp, digest = parts
    age = time.time() * 1000 - int(stamp)
    expected = hashlib.sha256((email + ":" + stamp + secret).encode()).hexdigest()
    if not hmac.compare_digest(digest, expected) or age < -300000 or age > 7 * 86400000:
        raise AccessDenied(401, "Your session has expired. Sign in to OC4D again")
    try:
        with urlopen(Request(os.environ["OC4D_BASE_URL"] + "/api/users/me", headers={"Authorization": "Bearer " + token}), timeout=5) as response:
            user = json.loads(response.read(65536))
    except HTTPError as error:
        raise AccessDenied(401, "Your OC4D session is no longer valid") from error
    except Exception as error:
        raise AccessDenied(503, "Could not verify your OC4D login. Try again shortly") from error
    if user.get("email") != email or user.get("role") not in {"SUPER_ADMIN", "SUPER", "ADMIN"}:
        raise AccessDenied(403, "Software updates are available to server superadmins only")
    return {"superadmin": True, "name": user.get("name", ""), "email": email}

API = "https://api.github.com/repos/storytold/deckcraft/releases/latest"
APPS = ("deckcraft", "wordcraft", "gridcraft", "pdfcraft", "vectorcraft", "cadcraft", "photocraft")
MAX_ARCHIVE = 80 * 1024 * 1024
MAX_UNPACKED = 240 * 1024 * 1024
ACTIVE_PHASES = {"queued", "installing", "retrying"}
MAINTENANCE_PAGE = b'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Deckcraft is updating</title><body style="margin:0;background:#edefeb;color:#232323;font:16px/1.5 system-ui;display:grid;place-items:center;min-height:100vh"><main style="max-width:480px;padding:32px;margin:20px;border-radius:24px;background:white"><h1 style="font-size:26px">Deckcraft is updating</h1><p>Presentations are temporarily unavailable. This page will reopen automatically when the update finishes.</p></main><script>async function check(){try{const r=await fetch('/api/maintenance',{cache:'no-store'});if(r.ok&&!(await r.json()).blocked){location.reload();return;}}catch(_){}setTimeout(check,1500);}check();</script></body></html>'''


def fetch(url, limit=MAX_ARCHIVE, progress=None):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "github.com"}:
        raise ValueError("Unexpected release source")
    with urlopen(Request(url, headers={"User-Agent": "CDN-Office-Suite", "Accept": "application/vnd.github+json"}), timeout=30) as response:
        data = bytearray()
        total = int(response.headers.get("Content-Length", "0"))
        while chunk := response.read(min(65536, limit + 1 - len(data))):
            data.extend(chunk)
            if len(data) > limit:
                raise ValueError("Release download is too large")
            if progress:
                progress(len(data), total)
    if len(data) > limit:
        raise ValueError("Release download is too large")
    return bytes(data)


def version(value):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value)
    if not match:
        raise ValueError("Unsupported release version")
    return tuple(map(int, match.groups()))


def latest_release(app="deckcraft", approved_version=None):
    if app not in APPS:
        raise ValueError("Unknown office app")
    route = "latest"
    if approved_version:
        version(approved_version)
        route = "tags/" + approved_version
    release = json.loads(fetch(f"https://api.github.com/repos/storytold/{app}/releases/{route}", 1024 * 1024))
    tag = release["tag_name"]
    version(tag)
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Only stable releases can be installed")
    name = app + "-web-" + tag.removeprefix("v") + ".zip"
    assets = {asset["name"]: asset for asset in release["assets"]}
    archive = assets[name]
    checksum = assets["SHA256SUMS.txt"]
    expected = f"https://github.com/storytold/{app}/releases/download/{tag}/"
    if archive["browser_download_url"] != expected + name or checksum["browser_download_url"] != expected + "SHA256SUMS.txt":
        raise ValueError("Unexpected release asset URL")
    if not 0 < archive["size"] <= MAX_ARCHIVE:
        raise ValueError("Release download is too large")
    return {"app": app, "version": tag, "archive": archive["browser_download_url"], "checksum": checksum["browser_download_url"],
            "name": name, "size": archive["size"], "notes": f"https://github.com/storytold/{app}/releases/tag/{tag}"}


def unpack_release(release, target, bundled=None, progress=None):
    notify = progress or (lambda *args, **kwargs: None)
    if bundled:
        archive = (bundled / release["name"]).read_bytes()
    elif progress:
        archive = fetch(release["archive"], progress=lambda size, total: notify("download", 5 + min(size / release["size"], 1) * 65, size, release["size"]))
    else:
        archive = fetch(release["archive"])
    if len(archive) != release["size"]:
        raise ValueError("Incomplete release download")
    notify("verify", 72)
    digest = hashlib.sha256(archive).hexdigest()
    sums = ((bundled / (release.get("app", "deckcraft") + "-SHA256SUMS.txt")).read_bytes() if bundled else fetch(release["checksum"], 1024 * 1024)).decode("utf-8")
    if not any(len(parts := line.split()) == 2 and parts[0] == digest and parts[1].lstrip("*") == release["name"] for line in sums.splitlines()):
        raise ValueError("Release checksum did not match")
    prefix = release["name"].removesuffix(".zip") + "/"
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        entries = bundle.infolist()
        if len(entries) > 5000 or sum(entry.file_size for entry in entries) > MAX_UNPACKED:
            raise ValueError("Release contents are too large")
        seen = set()
        for index, entry in enumerate(entries):
            if not entry.filename.startswith(prefix):
                raise ValueError("Unexpected archive layout")
            relative = entry.filename[len(prefix):]
            path = PurePosixPath(relative)
            if path.is_absolute() or ".." in path.parts or "\\" in relative or stat.S_ISLNK(entry.external_attr >> 16):
                raise ValueError("Unsafe archive entry")
            if not relative or entry.is_dir():
                continue
            if relative in seen or relative == "cdn-release.json" or relative.endswith(".gz"):
                raise ValueError("Unexpected archive entry")
            seen.add(relative)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(entry) as source, destination.open("wb") as output:
                shutil.copyfileobj(source, output)
            notify("unpack", 75 + 15 * (index + 1) / len(entries))
        if "index.html" not in seen or not any(name.endswith(".wasm") for name in seen) or not any(name.endswith(".js") for name in seen):
            raise ValueError("Web app assets are missing")
    (target / "cdn-release.json").write_text(json.dumps({"version": release["version"], "sha256": digest, "source": release["archive"]}))
    notify("prepare", 92)
    precompress(target)
    notify("prepare", 97)


def precompress(target):
    for path in target.rglob("*"):
        if path.is_file() and path.suffix in {".wasm", ".js", ".html", ".css"}:
            with path.open("rb") as source, gzip.open(str(path) + ".gz", "wb", compresslevel=6) as output:
                shutil.copyfileobj(source, output)


class Manager:
    def __init__(self, root, maintenance_grace=2, app="deckcraft", operation_lock=None, maintenance_file=None, operation_file=None):
        self.root = root
        self.app = app
        self.maintenance_file = maintenance_file or root / ".installer-maintenance"
        self.operation_file = operation_file or root / "operations.lock"
        self.file_lock = None
        self.maintenance_grace = maintenance_grace
        self.releases = root / "releases"
        self.releases.mkdir(parents=True, exist_ok=True)
        self.lock = operation_lock if operation_lock is not None else threading.Lock()
        self.cache_lock = threading.Lock()
        self.cached = None
        self.checked = 0
        self.state = {"phase": "idle", "message": ""}
        self.job = None
        self.worker = None
        self.retry_interval = 5
        self.last_saved = 0
        try:
            checked = json.loads((root / "checked.json").read_text())
            release, checked_at = checked["release"], checked["time"]
            version(release["version"])
            if not isinstance(checked_at, (int, float)) or not isinstance(release.get("notes"), str):
                raise ValueError("Invalid saved release check")
            self.cached, self.checked = release, checked_at
        except (OSError, ValueError, KeyError, TypeError):
            pass
        try:
            job = json.loads((root / "job.json").read_text())
            version(job["version"])
            if job["app"] != app:
                raise ValueError("Wrong app in saved job")
            if not isinstance(job["state"], dict) or job["state"].get("phase") not in ACTIVE_PHASES | {"complete", "error"}:
                raise ValueError("Invalid saved progress")
            self.job, self.state = job, job["state"]
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError):
            self.state = {"phase": "error", "message": "The saved update could not be read. Check again before approving a new update."}

    def save_json(self, name, value):
        temporary = self.root / (name + ".new")
        with temporary.open("w") as output:
            os.chmod(temporary, 0o600)
            json.dump(value, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, self.root / name)
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def update_state(self, force=True, **changes):
        self.state = {**self.state, **changes, "updatedAt": time.time()}
        if self.job and (force or time.monotonic() - self.last_saved >= 1):
            self.job["state"] = dict(self.state)
            self.save_json("job.json", self.job)
            self.last_saved = time.monotonic()

    def progress(self, step, percent, downloaded=None, total=None):
        labels = {"download": "Downloading your new tools…", "verify": "Checking the download…", "unpack": "Unpacking the new version…", "prepare": "Getting everything ready…"}
        changes = {"phase": "installing", "step": step, "progress": int(percent), "message": labels[step], "nextRetryAt": None}
        if downloaded is not None:
            changes.update(downloadedBytes=downloaded, totalBytes=total)
        self.update_state(force=self.state.get("step") != step, **changes)

    def active(self, name="current"):
        link = self.root / name
        if not link.is_symlink():
            return None
        resolved = link.resolve(strict=True)
        if resolved.parent != self.releases.resolve():
            raise ValueError("Release pointer is outside release storage")
        return resolved

    def installed(self, name="current"):
        active = self.active(name)
        return json.loads((active / "cdn-release.json").read_text())["version"] if active else None

    def point(self, name, destination):
        temp = self.root / (name + ".new")
        temp.unlink(missing_ok=True)
        temp.symlink_to(destination.relative_to(self.root), target_is_directory=True)
        os.replace(temp, self.root / name)

    def status(self):
        installed = self.installed()
        cached = self.cached
        result = {"app": self.app, "installed": installed, "previous": self.installed("previous"), "latest": cached["version"] if cached else None,
                  "available": bool(cached and (not installed or version(cached["version"]) > version(installed))),
                  "notes": cached["notes"] if cached else None, "checkedAt": self.checked or None, **self.state}
        if self.maintaining() and self.state["phase"] not in ACTIVE_PHASES:
            result.update(phase="installing", step="installer", progress=None, jobId=None, message="Software installation is in progress. Please wait…")
        return result

    def maintaining(self):
        if self.state["phase"] in ACTIVE_PHASES:
            return True
        try:
            marker = json.loads(self.maintenance_file.read_text())
            # A crashed installer must not leave the apps permanently locked.
            return Path(f"/proc/{int(marker['pid'])}/stat").read_text().split()[21] == marker["start"]
        except (OSError, ValueError, KeyError, IndexError):
            return False

    def check(self, fresh=False):
        with self.cache_lock:
            if fresh or not self.cached or time.time() - self.checked > 60:
                self.cached = latest_release(self.app)
                self.checked = time.time()
                self.save_json("checked.json", {"release": self.cached, "time": self.checked})
        return self.status()

    def acquire_operation(self):
        if not self.lock.acquire(blocking=False):
            return False
        try:
            import fcntl
            self.file_lock = self.operation_file.open("a")
            fcntl.flock(self.file_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except Exception:
            self.release_operation()
            return False

    def release_operation(self):
        if self.file_lock:
            self.file_lock.close()
            self.file_lock = None
        if self.lock.locked():
            self.lock.release()

    def begin(self, expected, rollback=False):
        version(expected)
        if not self.acquire_operation():
            raise ValueError("Another installation is already running")
        try:
            if rollback:
                target = self.active("previous")
                if not target or self.installed("previous") != expected:
                    raise ValueError("The previous release changed. Refresh before approving.")
            else:
                if self.installed() and version(expected) <= version(self.installed()):
                    raise ValueError("The app is already up to date")
                if not self.cached:
                    self.check(fresh=True)
                if self.cached["version"] != expected:
                    raise ValueError("The latest release changed. Check again before approving.")
                target = dict(self.cached)
            current, previous = self.active(), self.active("previous")
            self.job = {"id": secrets.token_hex(12), "app": self.app, "version": expected,
                        "rollback": rollback, "release": None if rollback else target,
                        "rollbackTarget": target.name if rollback else None,
                        "currentBefore": current.name if current else None,
                        "previousBefore": previous.name if previous else None,
                        "startedAt": time.time()}
            self.state = {}
            self.update_state(phase="queued", step="queued", progress=0, attempt=0,
                              jobId=self.job["id"], version=expected, startedAt=self.job["startedAt"],
                              nextRetryAt=None, message="Your update is saved on the server. Getting started…")
            self.worker = threading.Thread(target=self.install, args=(target, rollback), daemon=True)
            self.worker.start()
        except Exception:
            self.release_operation()
            raise

    def resume(self):
        if not self.job or self.state["phase"] not in ACTIVE_PHASES or (self.worker and self.worker.is_alive()):
            return False
        if not self.acquire_operation():
            return False
        try:
            for stale in self.releases.glob(".staging-*"):
                if stale.is_dir() and not stale.is_symlink():
                    shutil.rmtree(stale)
            rollback = self.job["rollback"]
            target = self.releases / self.job["rollbackTarget"] if rollback else self.job["release"]
            self.worker = threading.Thread(target=self.install, args=(target, rollback), daemon=True)
            self.worker.start()
        except Exception:
            self.release_operation()
            raise
        return True

    @staticmethod
    def transient(error):
        if isinstance(error, HTTPError):
            return error.code in {408, 429, 500, 502, 503, 504} or (error.code == 403 and error.headers.get("X-RateLimit-Remaining") == "0")
        if isinstance(error, (URLError, TimeoutError, ConnectionError, IncompleteRead)):
            return True
        if isinstance(error, OSError):
            return error.errno in {errno.ECONNRESET, errno.ECONNREFUSED, errno.ENETUNREACH, errno.EHOSTUNREACH, errno.ETIMEDOUT}
        return isinstance(error, ValueError) and str(error) == "Incomplete release download"

    def install(self, target, rollback=False):
        expected = self.job["version"] if self.job else (self.installed("previous") if rollback else target["version"])
        stage = None
        try:
            time.sleep(self.maintenance_grace)
            while True:
                try:
                    if self.job and self.installed() == expected:
                        self.update_state(phase="complete", step="done", progress=100, nextRetryAt=None,
                                          message="Update installed. Save your work, then reopen the app.", finishedAt=time.time())
                        return
                    wait = max(0, (self.state.get("nextRetryAt") or 0) - time.time())
                    if wait:
                        time.sleep(wait)
                    self.update_state(phase="installing", step="validate", progress=2,
                                      attempt=self.state.get("attempt", 0) + 1, nextRetryAt=None,
                                      message="Checking your approved version…")
                    if rollback:
                        destination = target
                        if destination.resolve().parent != self.releases.resolve() or not destination.is_dir():
                            raise ValueError("The previous release is no longer available")
                        if json.loads((destination / "cdn-release.json").read_text())["version"] != expected:
                            raise ValueError("The previous release changed. Review it again.")
                    else:
                        if self.job:
                            fresh = latest_release(self.app, expected)
                            if fresh["version"] != expected or any(fresh[key] != target[key] for key in ("size", "archive", "checksum")):
                                raise ValueError("The release changed. Check again and approve the new release.")
                        destination = self.releases / target["version"]
                        stage = self.releases / (".staging-" + secrets.token_hex(6))
                        stage.mkdir()
                        unpack_release(target, stage, progress=self.progress if self.job else None)
                        if destination.exists():
                            existing = json.loads((destination / "cdn-release.json").read_text())
                            downloaded = json.loads((stage / "cdn-release.json").read_text())
                            if existing != downloaded:
                                raise ValueError("Stored release differs from the verified download")
                            shutil.rmtree(stage)
                        else:
                            stage.rename(destination)
                        stage = None
                    self.update_state(step="activate", progress=98, message="Putting the new version in place…")
                    old = self.active()
                    if old:
                        self.point("previous", old)
                    self.point("current", destination)
                    self.update_state(phase="complete", step="done", progress=100, nextRetryAt=None,
                                      message="Previous release restored." if rollback else "All done! Save your work, then reopen the app.", finishedAt=time.time())
                    return
                except Exception as error:
                    if stage and stage.exists():
                        shutil.rmtree(stage)
                    stage = None
                    if self.installed() == expected:
                        self.state = {**self.state, "phase": "complete", "progress": 100, "message": "Update installed; the progress record could not be saved."}
                        logging.exception("Could not save completed update")
                        return
                    if self.job and self.transient(error):
                        delay = min(60, self.retry_interval * 2 ** min(self.state.get("attempt", 1) - 1, 6))
                        if isinstance(error, HTTPError):
                            try:
                                delay = max(delay, float(error.headers.get("Retry-After", "0")), float(error.headers.get("X-RateLimit-Reset", "0")) - time.time())
                            except ValueError:
                                pass
                        self.update_state(phase="retrying", step="waiting", nextRetryAt=time.time() + delay,
                                          message="The download connection paused. Your update is saved, and the server will try again automatically.")
                        logging.warning("%s update paused; retrying in %.1f seconds", self.app, delay)
                        continue
                    raise
        except Exception as error:
            logging.exception("Office update failed")
            if self.job:
                previous = self.job.get("previousBefore")
                if previous:
                    self.point("previous", self.releases / previous)
                else:
                    (self.root / "previous").unlink(missing_ok=True)
            self.update_state(phase="error", step="error", nextRetryAt=None,
                              message=str(error) + ". The active version is unchanged.")
        finally:
            if stage and stage.exists():
                shutil.rmtree(stage)
            self.release_operation()


class Handler(BaseHTTPRequestHandler):
    server_version = "CDNOffice/1"

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def managers(self):
        return getattr(self.server, "managers", {"deckcraft": self.server.manager})

    def origin(self):
        host = self.headers.get("Host", "").split(":")[0].lower()
        if host not in self.server.allowed_hosts:
            return False
        origin = self.headers.get("Origin")
        if origin:
            parsed = urlparse(origin)
            oc4d_port = urlparse(os.environ["OC4D_BASE_URL"]).port
            if parsed.hostname != host or parsed.scheme not in {"http", "https"} or parsed.port not in {None, oc4d_port, self.server.server_port}:
                return False
        return True

    def response_headers(self, code, mime="application/json", cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        if self.headers.get("Origin") and self.origin():
            self.send_header("Access-Control-Allow-Origin", self.headers["Origin"])
            self.send_header("Vary", "Origin, Accept-Encoding")

    def json(self, code, payload):
        data = json.dumps(payload).encode()
        self.response_headers(code)
        self.send_header("Content-Length", str(len(data)))
        try:
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            # The saved server job continues when the browser leaves before its receipt arrives.
            pass

    def do_OPTIONS(self):
        if not self.origin():
            return self.json(403, {"error": "Origin not allowed"})
        self.response_headers(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        if not self.origin():
            return self.json(403, {"error": "Host or origin not allowed"})
        path = unquote(urlparse(self.path).path)
        if path in {"/api/access", "/api/update-panel", "/api/admin-status"}:
            try:
                access = superadmin(self.headers.get("Authorization"))
            except AccessDenied as error:
                return self.json(error.status, {"error": str(error)})
            if path == "/api/access":
                return self.json(200, access)
            if path == "/api/admin-status":
                return self.json(200, {"apps": {app: manager.status() for app, manager in self.managers().items()}})
            data = Path(__file__).with_name("updates-panel.html").read_bytes()
            self.response_headers(200, "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/maintenance":
            app = parse_qs(urlparse(self.path).query).get("app", ["deckcraft"])[0]
            manager = self.managers().get(app)
            if not manager:
                return self.json(404, {"error": "Unknown app"})
            return self.json(200, {"blocked": manager.maintaining(), "installed": manager.installed()})
        if path == "/maintenance.js":
            data = Path(__file__).with_name("maintenance.js").read_bytes()
            self.response_headers(200, "text/javascript")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/status":
            status = {"installed": self.server.manager.installed(), "phase": self.server.manager.state["phase"]}
            status["apps"] = {app: {"installed": manager.installed(), "phase": "installing" if manager.maintaining() else manager.state["phase"]} for app, manager in self.managers().items()}
            status["tools"] = {name: available(port) for name, port in {"mail": self.server.mail_port}.items()}
            return self.json(200, status)
        app = path.split("/")[1] if "/" in path else ""
        manager = self.managers().get(app)
        if not manager or not path.startswith("/" + app + "/"):
            return self.json(404, {"error": "Not found"})
        if path == "/" + app + "/favicon.png":
            icon = Path(__file__).with_name("icons") / (app + "-icon.png")
            if not icon.is_file():
                return self.json(404, {"error": "App icon not installed"})
            data = icon.read_bytes()
            self.response_headers(200, "image/png", "no-cache")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if manager.maintaining():
            title = app.capitalize()
            page = MAINTENANCE_PAGE.replace(b"Deckcraft", title.encode()).replace(b"Presentations", b"This app").replace(b"/api/maintenance", ("/api/maintenance?app=" + app).encode())
            self.response_headers(503, "text/html; charset=utf-8")
            self.send_header("Retry-After", "5")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
            return
        relative = path[len(app) + 2:] or "index.html"
        parts = PurePosixPath(relative)
        if parts.is_absolute() or ".." in parts.parts or "\\" in relative or relative.startswith("."):
            return self.json(404, {"error": "Not found"})
        active = manager.active()
        if not active:
            return self.json(503, {"error": "The app is not installed"})
        source = active / relative
        # Keep old hashed assets available to tabs opened before the atomic switch.
        if not source.is_file() and re.fullmatch(app + r"-web-[a-f0-9]+(?:_bg)?\.(?:wasm|js)", relative):
            for release in manager.releases.iterdir():
                if not release.name.startswith(".") and (release / relative).is_file():
                    source = release / relative
                    break
        if not source.is_file() or manager.releases.resolve() not in source.resolve().parents:
            return self.json(404, {"error": "Not found"})
        if relative == "index.html":
            data = source.read_bytes()
            data = re.sub(rb"<link\b[^>]*\brel=[\"'][^\"']*\bicon\b[^\"']*[\"'][^>]*>", b"", data, flags=re.I)
            data = data.replace(b"</head>", ('<link rel="icon" type="image/png" href="/' + app + '/favicon.png"></head>').encode())
            data = data.replace(b"</body>", b'<script src="/maintenance.js"></script></body>')
            if "gzip" in self.headers.get("Accept-Encoding", ""):
                data = gzip.compress(data)
                self.response_headers(200, "text/html; charset=utf-8", "no-cache")
                self.send_header("Content-Encoding", "gzip")
            else:
                self.response_headers(200, "text/html; charset=utf-8", "no-cache")
            self.send_header("Vary", "Accept-Encoding")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        hashed = bool(re.search(r"-[a-f0-9]{8,64}(?:_bg)?\.(?:wasm|js)$", source.name))
        compressed = "gzip" in self.headers.get("Accept-Encoding", "") and Path(str(source) + ".gz").is_file()
        mime = "application/wasm" if source.suffix == ".wasm" else "text/javascript" if source.suffix == ".js" else mimetypes.guess_type(str(source))[0] or "application/octet-stream"
        if compressed:
            source = Path(str(source) + ".gz")
        self.response_headers(200, mime, "public, max-age=31536000, immutable" if hashed else "no-cache")
        self.send_header("Vary", "Accept-Encoding")
        if compressed:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(source.stat().st_size))
        self.end_headers()
        with source.open("rb") as content:
            shutil.copyfileobj(content, self.wfile)

    def do_POST(self):
        if not self.origin() or self.headers.get("Content-Type") != "application/json":
            return self.json(403, {"error": "Request not allowed"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 4096:
                return self.json(413, {"error": "Invalid request size"})
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict):
                raise ValueError("Invalid request")
            path = urlparse(self.path).path
            if path not in {"/api/check", "/api/update", "/api/rollback"}:
                return self.json(404, {"error": "Not found"})
            superadmin(self.headers.get("Authorization"))
            manager = self.managers().get(body.get("app", "deckcraft"))
            if not manager:
                raise ValueError("Unknown office app")
            if path == "/api/check":
                return self.json(200, manager.check())
            if path not in {"/api/update", "/api/rollback"}:
                return self.json(404, {"error": "Not found"})
            if body.get("approved") is not True or not isinstance(body.get("version"), str):
                raise ValueError("Approve a specific release before installing")
            manager.begin(body["version"], path == "/api/rollback")
            self.json(202, manager.status())
        except AccessDenied as error:
            self.json(error.status, {"error": str(error)})
        except (ValueError, KeyError, TypeError) as error:
            self.json(409, {"error": str(error)})
        except Exception:
            logging.exception("Release check failed")
            self.json(502, {"error": "Could not check GitHub. Check the Pi's internet connection and try again."})


def available(port):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


class Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(*args)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--mail-port", type=int, required=True)
    parser.add_argument("--hosts", required=True)
    args = parser.parse_args()
    try:
        base = urlparse(os.environ["OC4D_BASE_URL"])
        if base.scheme != "http" or base.hostname not in {"localhost", "127.0.0.1"} or base.path not in {"", "/"} or base.query or base.fragment or base.username:
            raise ValueError("OC4D_BASE_URL must specify the local OC4D service")
        ports = validate_ports({"port": args.port, "mailPort": args.mail_port, "oc4dPort": base.port})
        saved = json.loads((args.root / "installation.json").read_text())
        if validate_ports(saved) != ports or set(saved["apps"]) != set(APPS):
            raise ValueError("Runtime ports/apps differ from the installed configuration; rerun the installer")
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    logging.basicConfig(level=logging.INFO)
    import fcntl
    args.root.mkdir(parents=True, exist_ok=True)
    instance_lock = (args.root / "service.lock").open("a")
    fcntl.flock(instance_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    server = Server(("0.0.0.0", args.port), Handler)
    root = args.root.resolve()
    operation_lock = threading.Lock()
    server.managers = {app: Manager(root if app == "deckcraft" else root / app, app=app, operation_lock=operation_lock, maintenance_file=root / ".installer-maintenance", operation_file=root / "operations.lock") for app in APPS}
    server.mail_port = args.mail_port
    server.manager = server.managers["deckcraft"]
    server.allowed_hosts = set(args.hosts.lower().split(","))
    def recover_jobs():
        # Saved approvals survive browser disconnects and service restarts.
        while True:
            for manager in server.managers.values():
                try:
                    manager.resume()
                except Exception:
                    logging.exception("Could not resume saved update")
            time.sleep(2)
    threading.Thread(target=recover_jobs, daemon=True).start()
    server.serve_forever()


if __name__ == "__main__":
    main()
