import argparse
import sys
from pathlib import Path

from config import load_config
from graph import build_graph


def main():
    parser = argparse.ArgumentParser(description="Граф зависимостей пакета")
    parser.add_argument(
        "config",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "config.yaml"),
        help="путь к YAML-конфигурации",
    )
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except ValueError as error:
        print(f"Ошибка конфигурации:\n{error}", file=sys.stderr)
        return 1
    try:
        graph = build_graph(config, Path(args.config).resolve().parent)
    except ValueError as error:
        print(f"Ошибка получения зависимостей: {error}", file=sys.stderr)
        return 1
    if not graph:
        print("Граф пуст: исходный пакет исключён фильтром.")
    for package, dependencies in graph.items():
        if dependencies:
            print(f"{package} -> {', '.join(dependencies)}")
        else:
            print(package)
    return 0


if __name__ == "__main__":
    sys.exit(main())
