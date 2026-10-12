import hashlib
from http.server import ThreadingHTTPServer
import io
import json
import os
import time
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

import server
import bootstrap

TEST_SECRET = "private-test-secret-for-office-updates-123456789"


def login_token(email="super@example.test", timestamp=None, secret=TEST_SECRET):
    stamp = str(timestamp or int(time.time() * 1000))
    data = email + ":" + stamp
    return data + ":" + hashlib.sha256((data + secret).encode()).hexdigest()


def bundle(tag="v0.6.0", unsafe=False, app="deckcraft"):
    prefix = app + "-web-" + tag[1:] + "/"
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr(prefix + "index.html", "<html><body>release</body></html>")
        archive.writestr(prefix + app + "-web-0123456789abcdef.js", "// asset")
        archive.writestr(prefix + app + "-web-0123456789abcdef_bg.wasm", b"test wasm")
        if unsafe:
            archive.writestr(prefix + "../escape", "unsafe")
    data = stream.getvalue()
    release = {"version": tag, "archive": "archive", "checksum": "checksum", "name": prefix[:-1] + ".zip", "size": len(data), "notes": "https://github.com/storytold/deckcraft/releases/tag/" + tag}
    checksum = hashlib.sha256(data).hexdigest() + "  " + release["name"]
    return release, data, checksum.encode()


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def existing(self):
        manager = server.Manager(self.root, maintenance_grace=0)
        old = manager.releases / "v0.5.0"
        old.mkdir()
        (old / "cdn-release.json").write_text(json.dumps({"version": "v0.5.0"}))
        (old / "index.html").write_text("<html><body>original</body></html>")
        try:
            manager.point("current", old)
        except OSError:
            self.skipTest("Symlink tests require Linux or Windows symlink permission")
        return manager

    def unpack(self, target, release, data, sums):
        with patch.object(server, "fetch", side_effect=lambda url, *args: data if url == "archive" else sums):
            server.unpack_release(release, target)

    def test_verified_release_and_precompression(self):
        release, data, sums = bundle()
        self.unpack(self.root, release, data, sums)
        self.assertEqual(json.loads((self.root / "cdn-release.json").read_text())["version"], "v0.6.0")
        self.assertTrue((self.root / "index.html.gz").is_file())

    def test_checksum_failure_writes_nothing(self):
        release, data, _ = bundle()
        with self.assertRaisesRegex(ValueError, "checksum"):
            self.unpack(self.root, release, data, b"bad")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_traversal_rejected(self):
        release, data, sums = bundle(unsafe=True)
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            self.unpack(self.root, release, data, sums)
        self.assertFalse((self.root.parent / "escape").exists())

    def test_short_download_rejected(self):
        release, data, sums = bundle()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            self.unpack(self.root, release, data[:-1], sums)

    def test_atomic_update_and_rollback(self):
        manager = self.existing()
        release, data, sums = bundle()
        manager.lock.acquire()
        with patch.object(server, "fetch", side_effect=lambda url, *args: data if url == "archive" else sums):
            manager.install(release)
        self.assertEqual(manager.installed(), "v0.6.0")
        self.assertEqual(manager.installed("previous"), "v0.5.0")
        manager.lock.acquire()
        manager.install(manager.active("previous"), True)
        self.assertEqual(manager.installed(), "v0.5.0")
        self.assertEqual(manager.installed("previous"), "v0.6.0")

    def test_failed_update_keeps_active_release(self):
        manager = self.existing()
        release, data, _ = bundle()
        manager.lock.acquire()
        with patch.object(server, "fetch", side_effect=lambda url, *args: data if url == "archive" else b"bad"), self.assertLogs(level="ERROR"):
            manager.install(release)
        self.assertEqual(manager.installed(), "v0.5.0")
        self.assertEqual(manager.state["phase"], "error")
        self.assertFalse(manager.lock.locked())
        self.assertFalse(any(p.name.startswith(".staging") for p in manager.releases.iterdir()))

    def test_changed_release_requires_new_approval(self):
        manager = self.existing()
        release, _, _ = bundle("v0.7.0")
        with patch.object(server, "latest_release", return_value=release):
            with self.assertRaisesRegex(ValueError, "changed"):
                manager.begin("v0.6.0")
        self.assertFalse(manager.lock.locked())
        self.assertEqual(manager.installed(), "v0.5.0")

    def test_up_to_date_does_not_install(self):
        manager = self.existing()
        release, _, _ = bundle("v0.5.0")
        with patch.object(server, "latest_release", return_value=release):
            with self.assertRaisesRegex(ValueError, "up to date"):
                manager.begin("v0.5.0")
        self.assertEqual(manager.installed(), "v0.5.0")

    def test_api_auth_origin_and_approval(self):
        manager = self.existing()
        http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        http.manager = manager
        http.allowed_hosts = {"127.0.0.1"}
        thread = threading.Thread(target=http.serve_forever, daemon=True)
        thread.start()
        address = "http://127.0.0.1:" + str(http.server_port)
        def post(path, body, token=None, origin=None):
            headers = {"Content-Type": "application/json"}
            if token: headers["Authorization"] = "Bearer " + token
            if origin: headers["Origin"] = origin
            return urlopen(Request(address + path, data=json.dumps(body).encode(), headers=headers), timeout=5)
        environ = patch.dict(os.environ, {"AUTH_SECRET": TEST_SECRET, "OC4D_BASE_URL": "http://127.0.0.1:3000"})
        identity = patch.object(server, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(json.dumps({"email": "super@example.test", "role": "SUPER_ADMIN"}).encode()))
        environ.start()
        identity.start()
        try:
            for body, key, origin, expected in [({"approved": True, "version": "v0.6.0"}, None, None, 401),
                                                ({"version": "v0.6.0"}, login_token(), None, 409),
                                                ({"approved": True, "version": "v0.6.0"}, login_token(), "https://attacker.example", 403)]:
                with self.assertRaises(HTTPError) as error:
                    post("/api/update", body, key, origin)
                self.assertEqual(error.exception.code, expected)
            release, _, _ = bundle()
            with patch.object(server, "latest_release", return_value=release):
                result = json.load(post("/api/check", {}, login_token()))
            self.assertTrue(result["available"])
            self.assertEqual(manager.installed(), "v0.5.0")
            self.assertFalse(manager.lock.locked())
            manager.state = {"phase": "installing", "message": "Installing"}
            for resource in ["/deckcraft/index.html", "/deckcraft/deckcraft-web-0123456789abcdef_bg.wasm"]:
                with self.assertRaises(HTTPError) as error:
                    urlopen(address + resource, timeout=5)
                self.assertEqual(error.exception.code, 503)
                self.assertIn(b"Deckcraft is updating", error.exception.read())
            state = json.load(urlopen(address + "/api/maintenance", timeout=5))
            self.assertTrue(state["blocked"])
            manager.state = {"phase": "error", "message": "Preparation failed"}
            state = json.load(urlopen(address + "/api/maintenance", timeout=5))
            self.assertFalse(state["blocked"])
            index = urlopen(address + "/deckcraft/index.html", timeout=5).read()
            self.assertIn(b'original', index)
            self.assertIn(b'<script src="/maintenance.js">', index)
        finally:
            identity.stop()
            environ.stop()
            http.shutdown()
            http.server_close()

    def test_signed_session_and_database_role_required(self):
        with patch.dict(os.environ, {"AUTH_SECRET": TEST_SECRET, "OC4D_BASE_URL": "http://127.0.0.1:3000"}):
            for token in ["", "Bearer eyJhbGciOiJub25lIn0.eyJyb2xlIjoiU1VQRVJfQ.invalid", "Bearer " + login_token(secret="default-secret"), "Bearer " + login_token(timestamp=int((time.time()-8*86400)*1000))]:
                with self.assertRaises(server.AccessDenied) as error:
                    server.superadmin(token)
                self.assertEqual(error.exception.status, 401)
            for role in ["STUDENT", "TEACHER", "SUPER_ADMIN"]:
                with patch.object(server, "urlopen", side_effect=lambda *args, **kwargs: io.BytesIO(json.dumps({"email": "super@example.test", "role": role}).encode())):
                    if role == "SUPER_ADMIN":
                        self.assertTrue(server.superadmin("Bearer " + login_token())["superadmin"])
                    else:
                        with self.assertRaises(server.AccessDenied) as error:
                            server.superadmin("Bearer " + login_token())
                        self.assertEqual(error.exception.status, 403)

    def test_all_apps_verify_their_own_archive(self):
        for app in server.APPS:
            release, data, checksum = bundle(app=app)
            release['app'] = app
            target = self.root / app
            target.mkdir()
            with patch.object(server, 'fetch', side_effect=[data, checksum]):
                server.unpack_release(release, target)
            self.assertTrue((target / 'index.html').exists())
            self.assertTrue(list(target.glob(app + '*.wasm.gz')))

    def test_shared_lock_prevents_concurrent_app_update(self):
        lock = threading.Lock()
        lock.acquire()
        for app in server.APPS:
            manager = server.Manager(self.root / app, app=app, operation_lock=lock)
            with self.assertRaises(ValueError):
                manager.begin('v0.6.0')
        lock.release()

    def make_bundled_apps(self):
        folder = self.root / 'bundled'
        folder.mkdir()
        manifest = {}
        for app in server.APPS:
            release, data, checksum = bundle(app=app)
            manifest[app] = release
            (folder / release['name']).write_bytes(data)
            (folder / (app + '-SHA256SUMS.txt')).write_bytes(checksum)
        (folder / 'releases.json').write_text(json.dumps(manifest))
        return folder

    def test_fresh_offline_install_contains_every_craft_app(self):
        folder = self.make_bundled_apps()
        root = self.root / 'fresh-install'
        with patch.object(bootstrap.time, 'sleep'):
            bootstrap.prepare(root, folder)
        for app in server.APPS:
            manager = server.Manager(root if app == 'deckcraft' else root / app, app=app)
            self.assertEqual(manager.installed(), 'v0.6.0', app)
            self.assertTrue((manager.active() / 'index.html').is_file(), app)
            self.assertTrue(list(manager.active().glob(app + '*.wasm')), app)

    def test_bootstrap_failed_checksum_activates_nothing(self):
        folder = self.make_bundled_apps()
        (folder / 'gridcraft-SHA256SUMS.txt').write_text('invalid')
        root = self.root / 'install'
        with self.assertRaises(ValueError):
            bootstrap.prepare(root, folder)
        self.assertFalse((root / 'current').exists())
        self.assertFalse((root / 'wordcraft/current').exists())
        self.assertFalse((root / '.installer-maintenance').exists())

    def test_bootstrap_pointer_failure_restores_all_apps(self):
        folder = self.make_bundled_apps()
        root = self.root / 'install'
        original = server.Manager.point
        failed = False
        def fail_once(manager, name, destination):
            nonlocal failed
            if manager.app == 'wordcraft' and name == 'current' and not failed:
                failed = True
                raise OSError('simulated activation failure')
            original(manager, name, destination)
        with patch.object(server.Manager, 'point', fail_once), patch.object(bootstrap.time, 'sleep'):
            with self.assertRaises(OSError):
                bootstrap.prepare(root, folder)
        self.assertFalse((root / 'current').exists())
        self.assertFalse((root / 'wordcraft/current').exists())
        self.assertFalse((root / '.installer-maintenance').exists())


if __name__ == "__main__":
    unittest.main()
