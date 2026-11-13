import argparse
import sys
from pathlib import Path

from config import load_config


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
    for name, value in config.items():
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{name}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
