import json
from pathlib import Path
import tempfile
import unittest
from remove_legacy import recognized, remove


class LegacyTests(unittest.TestCase):
    def test_package_identity_required(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            self.assertFalse(recognized(path, {'etherpad'}))
            (path / 'package.json').write_text(json.dumps({'name': 'other-app'}))
            self.assertFalse(recognized(path, {'etherpad'}))
            (path / 'package.json').write_text(json.dumps({'name': 'etherpad'}))
            self.assertTrue(recognized(path, {'etherpad'}))

    def test_unrecognized_folder_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            app = home / 'etherpad-lite'
            app.mkdir()
            (app / 'package.json').write_text(json.dumps({'name': 'different-software'}))
            with self.assertRaises(ValueError):
                remove(home, home / 'office', home / 'website', dry_run=True)
            self.assertTrue(app.exists())

    def test_symlink_install_is_never_followed(self):
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            target = home / 'unrelated'
            target.mkdir()
            try:
                (home / 'etherpad-lite').symlink_to(target, target_is_directory=True)
            except OSError:
                self.skipTest('Symlink permission unavailable')
            with self.assertRaises(ValueError):
                remove(home, home / 'office', home / 'website', dry_run=True)
            self.assertTrue(target.exists())
