import sys
import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))

from maven import get_dependencies, parse_dependencies


class MavenTests(unittest.TestCase):
    def test_download_and_parse_dependencies(self):
        content = (PROJECT_DIR / "tests/repository.pom").read_bytes()
        config = {
            "package_name": "org.example:demo",
            "repository": "https://example.org/maven/",
            "test_mode": False,
            "version": "1.0",
        }
        for version in ("1.0", "2.0"):
            with self.subTest(version=version):
                config["version"] = version
                with patch("maven.urlopen", return_value=BytesIO(content)) as request:
                    dependencies = get_dependencies(config)
                request.assert_called_once_with(
                    f"https://example.org/maven/org/example/demo/{version}/demo-{version}.pom",
                    timeout=15,
                )
                self.assertEqual(dependencies, [
                    ("org.example", "library", "2.0"),
                    ("org.example", "tests", "1.2"),
                    ("org.example", "inherited-version", ""),
                ])
        self.assertEqual(parse_dependencies(b"<project/>", "org.example:demo", "1.0"), [])
        content = b"<project><dependencies><dependency><groupId>g</groupId><artifactId>a</artifactId><version>${project.version}</version></dependency></dependencies></project>"
        self.assertEqual(parse_dependencies(content, "org.example:demo", "2.0"), [("g", "a", "2.0")])

    def test_repository_and_pom_errors(self):
        config = {
            "package_name": "org.example:demo",
            "repository": "https://example.org/maven/",
            "test_mode": False,
            "version": "1.0",
        }
        errors = (
            HTTPError(config["repository"], 404, "Not Found", None, None),
            URLError("connection failed"),
            TimeoutError("timeout"),
        )
        for error in errors:
            with self.subTest(error=error):
                with patch("maven.urlopen", side_effect=error):
                    with self.assertRaisesRegex(ValueError, "загрузить POM"):
                        get_dependencies(config)
        invalid_documents = (
            b"<project>",
            b"<html/>",
            b"<project><dependencies><dependency/></dependencies></project>",
            b"<project><properties><v>${v}x</v></properties><dependencies><dependency><groupId>g</groupId><artifactId>a</artifactId><version>${v}</version></dependency></dependencies></project>",
        )
        for content in invalid_documents:
            with self.subTest(content=content):
                with self.assertRaises(ValueError):
                    parse_dependencies(content, "org.example:demo", "1.0")



if __name__ == "__main__":
    unittest.main()
