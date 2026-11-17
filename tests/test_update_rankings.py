import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("updater", Path(__file__).resolve().parents[1] / "scripts/update_rankings.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


class RankingTests(unittest.TestCase):
    def test_render_star_change_and_new_entry(self):
        repo = {"name": "example/model", "url": "https://github.com/example/model", "stars": 150, "forks": 10, "size_kb": 2048, "language": "Python"}
        snapshot = {"updated_at": "2026-01-01", "repositories": [repo]}
        previous = {"repositories": [{"name": "example/model", "stars": 100}]}
        self.assertIn("| +50 |", updater.render(snapshot, previous))
        self.assertIn("| 2.0 |", updater.render(snapshot, previous))
        self.assertIn("| — |", updater.render(snapshot, {}))

    def test_api_failure_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("existing ranking")
            with patch.object(updater, "ROOT", root), patch.object(updater, "fetch_repositories", side_effect=RuntimeError("API unavailable")):
                with self.assertRaises(RuntimeError):
                    updater.main()
            self.assertEqual((root / "README.md").read_text(), "existing ranking")
            self.assertFalse((root / "data").exists())


if __name__ == "__main__":
    unittest.main()
