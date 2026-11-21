"""Тесты для модуля graph: построение графа, фильтрация и циклы."""
# flake8: noqa
from graph import build_graph, get_load_order, to_d2
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml


PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR / "src"))


class GraphTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "package_name": "A",
            "repository": "repository.yaml",
            "test_mode": True,
            "version": "1.0",
            "max_depth": 3,
            "filter_substring": "",
        }

    def test_depth_filter_and_cycles(self):
        cases = [
            ("A", 0, "", {"A": []}),
            ("A", 1, "", {"A": ["B", "C"], "B": [], "C": []}),
            ("A", 2, "", {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}),
            (
                "A",
                10,
                "",
                {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": ["A", "E"], "E": []},
            ),
            ("A", 3, "B", {"A": ["C"], "C": ["D"], "D": ["A", "E"], "E": []}),
            ("A", 3, "D", {"A": ["B", "C"], "B": [], "C": []}),
            ("A", 3, "A", {}),
            ("F", 3, "", {"F": []}),
            ("G", 10, "", {"G": ["G"]}),
        ]
        for root, depth, substring, expected in cases:
            with self.subTest(root=root, depth=depth, substring=substring):
                self.config["package_name"] = root
                self.config["max_depth"] = depth
                self.config["filter_substring"] = substring
                graph = build_graph(self.config, PROJECT_DIR / "tests")
                self.assertEqual(graph, expected)
                self.assertEqual(list(graph), list(expected))

    def test_maven_bfs(self):
        self.config.update(
            {
                "package_name": "org.example:a",
                "repository": "https://example.org/maven/",
                "test_mode": False,
                "max_depth": 2,
            }
        )
        dependencies = [
            [("org.example", "b", "1.0"), ("org.example", "c", "1.0")],
            [("org.example", "d", "1.0"), ("org.example", "a", "1.0")],
            [("org.example", "d", "1.0")],
        ]
        with patch("graph.get_dependencies", side_effect=dependencies) as request:
            graph = build_graph(self.config, PROJECT_DIR)
        self.assertEqual(
            graph,
            {
                "org.example:a:1.0": ["org.example:b:1.0", "org.example:c:1.0"],
                "org.example:b:1.0": ["org.example:d:1.0", "org.example:a:1.0"],
                "org.example:c:1.0": ["org.example:d:1.0"],
                "org.example:d:1.0": [],
            },
        )
        self.assertEqual(
            [item.args[0]["package_name"] for item in request.call_args_list],
            ["org.example:a", "org.example:b", "org.example:c"],
        )
        self.config["max_depth"] = 0
        with patch("graph.get_dependencies") as request:
            self.assertEqual(
                build_graph(self.config, PROJECT_DIR), {"org.example:a:1.0": []}
            )
            request.assert_not_called()
        self.config["max_depth"] = 2
        with patch("graph.get_dependencies", return_value=[("org.example", "b", "")]):
            with self.assertRaisesRegex(ValueError, "версия"):
                build_graph(self.config, PROJECT_DIR)

    def test_load_order(self):
        cases = [
            ("H", 3, "", ["K", "I", "J", "H"]),
            ("H", 1, "", ["I", "J", "H"]),
            ("H", 0, "", ["H"]),
            ("H", 3, "I", ["K", "J", "H"]),
            ("H", 3, "H", []),
            ("F", 3, "", ["F"]),
        ]
        for root, depth, substring, expected in cases:
            with self.subTest(root=root, depth=depth, substring=substring):
                self.config["package_name"] = root
                self.config["max_depth"] = depth
                self.config["filter_substring"] = substring
                graph = build_graph(self.config, PROJECT_DIR / "tests")
                order = get_load_order(graph)
                self.assertEqual(order, expected)
                for package, dependencies in graph.items():
                    for dependency in dependencies:
                        self.assertLess(order.index(dependency), order.index(package))

    def test_load_order_with_cycles(self):
        for root in ("A", "G"):
            with self.subTest(root=root):
                self.config["package_name"] = root
                graph = build_graph(self.config, PROJECT_DIR / "tests")
                with self.assertRaisesRegex(ValueError, "цикл"):
                    get_load_order(graph)

    def test_d2(self):
        cases = [
            ({}, ""),
            ({"A": []}, 'n0: "A"'),
            ({"A": ["A"]}, 'n0: "A"\nn0 -> n0'),
            (
                {"A": ["B"], "B": ["A"]},
                'n0: "A"\nn1: "B"\nn0 -> n1\nn1 -> n0',
            ),
            (
                {"org.example:a:1.0": ["org.example:b:2.0"], "org.example:b:2.0": []},
                'n0: "org.example:a:1.0"\nn1: "org.example:b:2.0"\nn0 -> n1',
            ),
            ({'a"b': []}, 'n0: "a\\"b"'),
        ]
        for graph, expected in cases:
            with self.subTest(graph=graph):
                self.assertEqual(to_d2(graph), expected)

    def test_invalid_test_repository(self):
        with tempfile.TemporaryDirectory(dir=PROJECT_DIR / "tests") as directory:
            path = Path(directory) / "repository.yaml"
            self.config["repository"] = str(path)
            invalid = [
                [],
                {"a": []},
                {"A": "B"},
                {"A": ["B"]},
                {"A": [1]},
                {"B": []},
            ]
            for repository in invalid:
                with self.subTest(repository=repository):
                    path.write_text(yaml.safe_dump(repository), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        build_graph(self.config, Path(directory))
            path.write_text("A: [", encoding="utf-8")
            with self.assertRaises(ValueError):
                build_graph(self.config, Path(directory))
            path.unlink()
            with self.assertRaises(ValueError):
                build_graph(self.config, Path(directory))


if __name__ == "__main__":
    unittest.main()
