import argparse
import sys
from pathlib import Path

from config import load_config
from maven import get_dependencies


def main():
    parser = argparse.ArgumentParser(description="Настройки анализа зависимостей пакета")
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
        dependencies = get_dependencies(config, Path(args.config).resolve().parent)
    except ValueError as error:
        print(f"Ошибка получения зависимостей: {error}", file=sys.stderr)
        return 1
    if not dependencies:
        print("Прямых зависимостей нет.")
    for group, artifact, version in dependencies:
        if version:
            print(f"{group}:{artifact}:{version}")
        else:
            print(f"{group}:{artifact} (версия не указана в POM)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
