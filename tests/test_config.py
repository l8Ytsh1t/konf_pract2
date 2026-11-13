import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from config import PARAMETERS, load_config


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=PROJECT_DIR / "tests")
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "config.yaml"
        self.config = {
            "package_name": "example",
            "repository": "https://example.org/packages",
            "test_mode": False,
            "version": "1.0",
            "max_depth": 3,
            "filter_substring": "",
        }

    def write_config(self):
        self.path.write_text(yaml.safe_dump(self.config), encoding="utf-8")

    def run_cli(self):
        return subprocess.run(
            [str(PROJECT_DIR / "run.sh"), str(self.path)],
            capture_output=True,
            text=True,
            cwd=PROJECT_DIR / "tests",
        )

    def test_valid_config_and_output(self):
        self.config["filter_substring"] = "lib"
        self.write_config()
        self.assertEqual(load_config(self.path), self.config)
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout.splitlines(), [
            "package_name: example",
            "repository: https://example.org/packages",
            "test_mode: false",
            "version: 1.0",
            "max_depth: 3",
            "filter_substring: lib",
        ])

    def test_invalid_parameter_values(self):
        invalid_values = {
            "package_name": ["", 12],
            "repository": ["", "example.org", "https://host:bad"],
            "test_mode": ["false", 0],
            "version": ["", 1.0],
            "max_depth": [-1, 1.5, True],
            "filter_substring": [3],
        }
        for name, values in invalid_values.items():
            original = self.config[name]
            for value in values:
                with self.subTest(parameter=name, value=value):
                    self.config[name] = value
                    self.write_config()
                    with self.assertRaisesRegex(ValueError, name):
                        load_config(self.path)
            self.config[name] = original

    def test_missing_parameters(self):
        for name in PARAMETERS:
            with self.subTest(parameter=name):
                value = self.config.pop(name)
                self.write_config()
                with self.assertRaisesRegex(ValueError, name):
                    load_config(self.path)
                self.config[name] = value

    def test_test_repository_paths(self):
        repository = self.path.parent / "repository.txt"
        repository.write_text("", encoding="utf-8")
        self.config["test_mode"] = True
        for filename in (repository.name, str(repository)):
            with self.subTest(filename=filename):
                self.config["repository"] = filename
                self.write_config()
                self.assertEqual(load_config(self.path), self.config)

    def test_unavailable_test_repository(self):
        self.config["test_mode"] = True
        for filename in ("missing.txt", str(self.path.parent)):
            with self.subTest(filename=filename):
                self.config["repository"] = filename
                self.write_config()
                with self.assertRaisesRegex(ValueError, "repository"):
                    load_config(self.path)

    def test_invalid_configuration_file(self):
        with self.assertRaisesRegex(ValueError, "прочитать"):
            load_config(self.path)
        for content in ("key: [", "", "- item"):
            with self.subTest(content=content):
                self.path.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_config(self.path)

    def test_cli_reports_errors_for_all_parameters(self):
        self.config = {name: None for name in PARAMETERS}
        self.write_config()
        result = self.run_cli()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("Traceback", result.stderr)
        for name in PARAMETERS:
            self.assertIn(name + ":", result.stderr)



if __name__ == "__main__":
    unittest.main()
