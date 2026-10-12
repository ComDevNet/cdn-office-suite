import http.client
from http.server import ThreadingHTTPServer
import json
import subprocess
import sys
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import URLError

import server
from test_server import bundle


class JobTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manager = server.Manager(self.root, maintenance_grace=0)
        old = self.manager.releases / 'v0.5.0'
        old.mkdir()
        (old / 'cdn-release.json').write_text(json.dumps({'version': 'v0.5.0'}))
        (old / 'index.html').write_text('original')
        self.manager.point('current', old)
        self.release, self.data, self.sums = bundle()
        self.manager.cached = self.release
        self.manager.retry_interval = .15

    def tearDown(self):
        if self.manager.worker and self.manager.worker.is_alive():
            self.manager.worker.join(3)
        self.temp.cleanup()

    def fetch(self, url, *args, **kwargs):
        data = self.data if url == 'archive' else self.sums
        if kwargs.get('progress'):
            kwargs['progress'](len(data), len(data))
        return data

    def wait_phase(self, phase, manager=None):
        manager = manager or self.manager
        end = time.monotonic() + 3
        while time.monotonic() < end:
            if manager.state['phase'] == phase:
                return
            time.sleep(.005)
        self.fail(str(manager.state))

    def wait_saved(self, key, value):
        end = time.monotonic() + 3
        while time.monotonic() < end:
            state = json.loads((self.root / 'job.json').read_text())['state']
            if state.get(key) == value:
                return state
            time.sleep(.005)
        self.fail(str(state))

    def saved_job(self):
        with patch.object(threading.Thread, 'start'):
            self.manager.begin('v0.6.0')
        self.manager.release_operation()
        return server.Manager(self.root, maintenance_grace=0)

    def test_disconnect_does_not_stop_job_and_progress_is_saved(self):
        gate = threading.Event()
        original = server.unpack_release
        def unpack(release, stage, **kwargs):
            kwargs['progress']('download', 40, 200, 500)
            gate.wait(3)
            original(release, stage, **kwargs)
        http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        http.manager = self.manager
        http.allowed_hosts = {'127.0.0.1'}
        threading.Thread(target=http.serve_forever, daemon=True).start()
        try:
            with patch.object(server, 'superadmin', return_value={'superadmin': True}), patch.object(server, 'latest_release', return_value=self.release), patch.object(server, 'fetch', side_effect=self.fetch), patch.object(server, 'unpack_release', side_effect=unpack):
                client = http_client(http.server_port)
                client.request('POST', '/api/update', json.dumps({'approved': True, 'version': 'v0.6.0'}), {'Content-Type': 'application/json'})
                client.close()
                self.wait_phase('installing')
                end = time.monotonic() + 2
                while self.manager.state.get('progress') != 40 and time.monotonic() < end:
                    time.sleep(.005)
                self.wait_saved('progress', 40)
                recovered = server.Manager(self.root)
                self.assertEqual(recovered.status()['progress'], 40)
                self.assertTrue(recovered.maintaining())
                self.assertEqual(recovered.installed(), 'v0.5.0')
                gate.set()
                self.manager.worker.join(3)
                self.assertEqual(self.manager.installed(), 'v0.6.0')
                self.assertEqual(self.manager.state['progress'], 100)
        finally:
            gate.set()
            http.shutdown()
            http.server_close()

    def test_internet_failure_retries_without_a_browser(self):
        with patch.object(server, 'latest_release', side_effect=[URLError('offline'), self.release]), patch.object(server, 'fetch', side_effect=self.fetch):
            self.manager.begin('v0.6.0')
            self.wait_phase('retrying')
            self.wait_saved('phase', 'retrying')
            saved = json.loads((self.root / 'job.json').read_text())
            self.assertEqual(saved['version'], 'v0.6.0')
            self.assertGreater(saved['state']['nextRetryAt'], time.time())
            self.assertTrue(self.manager.maintaining())
            self.manager.worker.join(3)
        self.assertEqual(self.manager.installed(), 'v0.6.0')
        self.assertEqual(self.manager.state['attempt'], 2)
        self.assertFalse(self.manager.maintaining())

    def test_service_restart_recovers_saved_approval(self):
        recovered = self.saved_job()
        stale = recovered.releases / '.staging-interrupted'
        stale.mkdir()
        (stale / 'partial').write_text('interrupted')
        with patch.object(server, 'latest_release', return_value=self.release), patch.object(server, 'fetch', side_effect=self.fetch):
            self.assertTrue(recovered.resume())
            recovered.worker.join(3)
        self.assertEqual(recovered.installed(), 'v0.6.0')
        self.assertEqual(recovered.installed('previous'), 'v0.5.0')
        self.assertFalse(stale.exists())
        self.assertFalse(recovered.resume())

    def test_fresh_process_recovers_approved_job(self):
        self.saved_job()
        (self.root / 'fixture.zip').write_bytes(self.data)
        (self.root / 'fixture.sums').write_bytes(self.sums)
        (self.root / 'fixture.release').write_text(json.dumps(self.release))
        code = """
import json, sys
from pathlib import Path
from unittest.mock import patch
import server
root = Path(sys.argv[1])
release = json.loads((root / 'fixture.release').read_text())
def fetch(url, *args, **kwargs):
    return (root / ('fixture.zip' if url == 'archive' else 'fixture.sums')).read_bytes()
manager = server.Manager(root, maintenance_grace=0)
with patch.object(server, 'latest_release', return_value=release), patch.object(server, 'fetch', side_effect=fetch):
    assert manager.resume()
    manager.worker.join(5)
assert manager.state['phase'] == 'complete', manager.state
assert manager.installed() == 'v0.6.0'
assert manager.installed('previous') == 'v0.5.0'
"""
        result = subprocess.run([sys.executable, '-c', code, str(self.root)], cwd=Path(server.__file__).parent, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.root / 'job.json').read_text())['state']['progress'], 100)

    def test_crash_after_activation_does_not_replay_or_lose_rollback(self):
        recovered = self.saved_job()
        new = recovered.releases / 'v0.6.0'
        new.mkdir()
        (new / 'cdn-release.json').write_text(json.dumps({'version': 'v0.6.0'}))
        recovered.point('previous', recovered.active())
        recovered.point('current', new)
        with patch.object(server, 'latest_release', side_effect=AssertionError('No second download')):
            recovered.resume()
            recovered.worker.join(3)
        self.assertEqual(recovered.state['phase'], 'complete')
        self.assertEqual(recovered.installed('previous'), 'v0.5.0')
        self.assertEqual(json.loads((self.root / 'job.json').read_text())['state']['progress'], 100)

    def test_checksum_failure_stops_without_retry_or_activation(self):
        with patch.object(server, 'latest_release', return_value=self.release) as latest, patch.object(server, 'fetch', side_effect=lambda url, **kw: self.data if url == 'archive' else b'bad'), self.assertLogs(level='ERROR'):
            self.manager.begin('v0.6.0')
            self.manager.worker.join(3)
        self.assertEqual(latest.call_count, 1)
        self.assertEqual(self.manager.state['phase'], 'error')
        self.assertEqual(self.manager.installed(), 'v0.5.0')
        self.assertFalse(self.manager.lock.locked())

    def test_changed_release_requires_new_approval_after_queueing(self):
        newer, _, _ = bundle('v0.7.0')
        with patch.object(server, 'latest_release', return_value=newer), self.assertLogs(level='ERROR'):
            self.manager.begin('v0.6.0')
            self.manager.worker.join(3)
        self.assertEqual(self.manager.state['phase'], 'error')
        self.assertEqual(self.manager.installed(), 'v0.5.0')


def http_client(port):
    return http.client.HTTPConnection('127.0.0.1', port, timeout=3)
