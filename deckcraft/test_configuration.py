import json
import os
import socket
import subprocess
import sys
import server
from pathlib import Path
import tempfile
import unittest
from configuration import saved_ports, resolve_ports, validate_ports


class ConfigurationTests(unittest.TestCase):
    def test_rerun_retains_custom_ports_and_only_explicit_override_changes_them(self):
        saved = {'port': 8877, 'oc4dPort': 3333, 'mailPort': 2222}
        self.assertEqual(resolve_ports(saved), saved)
        self.assertEqual(resolve_ports(saved, port=8878), {**saved, 'port': 8878})

    def test_invalid_or_colliding_ports_are_rejected(self):
        for bad in [None, '', '8769', 0, 80, 65536, True]:
            with self.assertRaises(ValueError):
                validate_ports({'port': bad, 'oc4dPort': 3000, 'mailPort': 2000})
        with self.assertRaises(ValueError):
            resolve_ports({'port': 8877, 'oc4dPort': 3333, 'mailPort': 2222}, mail_port=8877)

    def test_upgrade_migrates_actual_old_ports_without_using_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, module = root / 'data', root / 'module'
            data.mkdir(); module.mkdir()
            (module / 'settings.js').write_text('window.OFFICE_CONFIG={"port":8877,"mailPort":2222};')
            (data / 'service.env').write_text('OC4D_BASE_URL=http://127.0.0.1:3333\n')
            self.assertEqual(saved_ports(data, module), {'port': 8877, 'mailPort': 2222, 'oc4dPort': 3333})
            (data / 'installation.json').write_text(json.dumps({'port': 9988, 'oc4dPort': 3333, 'mailPort': 2222}))
            self.assertEqual(saved_ports(data, module)['port'], 9988)

    def test_missing_or_corrupt_existing_config_does_not_guess_ports(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            module = data / 'module'
            module.mkdir()
            self.assertIsNone(saved_ports(data, module))
            (data / 'service.env').write_text('OC4D_BASE_URL=http://127.0.0.1:3333')
            with self.assertRaises(ValueError):
                saved_ports(data, module)
            (data / 'installation.json').write_text('{}')
            with self.assertRaises(ValueError):
                saved_ports(data, module)

    def test_occupied_port_stops_host_instead_of_selecting_another(self):
        with tempfile.TemporaryDirectory() as tmp, socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            port = occupied.getsockname()[1]
            root = Path(tmp)
            ports = {'port': port, 'oc4dPort': 3000, 'mailPort': 2000}
            (root / 'installation.json').write_text(json.dumps({**ports, 'apps': list(server.APPS)}))
            process = subprocess.run([sys.executable, server.__file__, '--root', str(root), '--port', str(port), '--mail-port', '2000', '--hosts', '127.0.0.1'], env={**os.environ, 'OC4D_BASE_URL':'http://127.0.0.1:3000'}, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('Address already in use', process.stderr)

    def test_host_rejects_runtime_port_that_differs_from_saved_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'installation.json').write_text(json.dumps({'port':8769, 'oc4dPort':3000, 'mailPort':2000, 'apps':list(server.APPS)}))
            process = subprocess.run([sys.executable, server.__file__, '--root', str(root), '--port', '8877', '--mail-port', '2000', '--hosts', '127.0.0.1'], env={**os.environ, 'OC4D_BASE_URL':'http://127.0.0.1:3000'}, capture_output=True, text=True, timeout=5)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('differ from the installed configuration', process.stderr)
            self.assertFalse((root / 'service.lock').exists())
