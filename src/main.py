import argparse
import sys
from pathlib import Path

from config import load_config
from graph import build_graph, get_load_order


def main():
    parser = argparse.ArgumentParser(description="Граф зависимостей пакета")
    parser.add_argument(
        "config",
        nargs="?",
        default=str(Path(__file__).resolve().parent.parent / "config.yaml"),
        help="путь к YAML-конфигурации",
    )
    parser.add_argument(
        "--load-order",
        action="store_true",
        help="вывести порядок загрузки: зависимости перед зависящими от них пакетами",
    )
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except ValueError as error:
        print(f"Ошибка конфигурации:\n{error}", file=sys.stderr)
        return 1
    try:
        graph = build_graph(config, Path(args.config).resolve().parent)
        if args.load_order:
            order = get_load_order(graph)
    except ValueError as error:
        print(f"Ошибка анализа зависимостей: {error}", file=sys.stderr)
        return 1
    if not graph:
        print("Граф пуст: исходный пакет исключён фильтром.")
        return 0
    if args.load_order:
        for package in order:
            print(package)
        return 0
    for package, dependencies in graph.items():
        if dependencies:
            print(f"{package} -> {', '.join(dependencies)}")
        else:
            print(package)
    return 0


if __name__ == "__main__":
    sys.exit(main())
