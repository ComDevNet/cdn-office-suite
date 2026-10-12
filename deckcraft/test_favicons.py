import http.client
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import server


class FaviconTests(unittest.TestCase):
    def test_every_editor_gets_its_own_icon_including_during_maintenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            icons = root / 'icons'
            icons.mkdir()
            manager = server.Manager(root / 'data')
            release = manager.releases / 'v0.5.0'
            release.mkdir()
            (release / 'cdn-release.json').write_text(json.dumps({'version': 'v0.5.0'}))
            (release / 'index.html').write_text('<html><head><link rel="icon" href="missing.png"></head><body>editor</body></html>')
            manager.point('current', release)
            for app in server.APPS:
                (icons / (app + '-icon.png')).write_bytes(b'\x89PNG\r\n\x1a\n' + app.encode())
            host = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
            host.manager = manager
            host.managers = {app: manager for app in server.APPS}
            host.allowed_hosts = {'127.0.0.1'}
            host.mail_port = 2222
            thread = threading.Thread(target=host.serve_forever, daemon=True)
            with patch.object(server, '__file__', str(root / 'server.py')):
                thread.start()
                try:
                    with patch.object(server, 'available', return_value=True) as probe:
                        client = http.client.HTTPConnection('127.0.0.1', host.server_port, timeout=3)
                        client.request('GET', '/api/status')
                        self.assertTrue(json.loads(client.getresponse().read())['tools']['mail'])
                        probe.assert_called_once_with(2222)
                        client.close()
                    for app in server.APPS:
                        client = http.client.HTTPConnection('127.0.0.1', host.server_port, timeout=3)
                        client.request('GET', '/' + app + '/index.html')
                        response = client.getresponse()
                        html = response.read().decode()
                        self.assertEqual(response.status, 200)
                        self.assertIn('href="/' + app + '/favicon.png"', html)
                        self.assertNotIn('missing.png', html)
                        manager.state = {'phase': 'retrying'}
                        client.request('GET', '/' + app + '/favicon.png')
                        response = client.getresponse()
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.getheader('Content-Type'), 'image/png')
                        self.assertEqual(response.read(), (icons / (app + '-icon.png')).read_bytes())
                        manager.state = {'phase': 'idle'}
                        client.close()
                finally:
                    host.shutdown()
                    host.server_close()
                    thread.join(3)
