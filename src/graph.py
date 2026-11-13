"""Модуль для построения графа зависимостей."""

import json
import re
from collections import deque
from pathlib import Path

import yaml

from maven import get_dependencies

MAVEN_COORDINATES_LENGTH = 3


def load_test_repository(filename):
    """Загружает и валидирует тестовый репозиторий из YAML."""
    try:
        with Path(filename).open(encoding="utf-8") as file:
            repository = yaml.safe_load(file)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(
            f"Не удалось прочитать тестовый репозиторий: {error}"
        ) from error
    if not isinstance(repository, dict):
        raise ValueError(
            "Тестовый репозиторий должен содержать пары пакет: список зависимостей"
        )
    for name, dependencies in repository.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z]+", name):
            raise ValueError(
                "Имена тестовых пакетов должны состоять из больших латинских букв"
            )
        if not isinstance(dependencies, list):
            raise ValueError(f"Зависимости пакета {name} должны быть списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in repository:
                raise ValueError(
                    f"Неизвестная зависимость {dependency} у пакета {name}"
                )
    return repository


def get_node_dependencies(node, config, test_mode, repository):
    """Получает прямые зависимости для одного узла графа."""
    if test_mode:
        return repository[node]

    parts = node.split(":")
    if len(parts) != MAVEN_COORDINATES_LENGTH or not re.fullmatch(
        r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", parts[2]
    ):
        raise ValueError(
            f"Для анализа пакета {node} в POM не указана конкретная версия"
        )

    package_config = config.copy()
    package_config["package_name"] = ":".join(parts[:2])
    package_config["version"] = parts[2]

    dependencies = []
    for group, artifact, version in get_dependencies(package_config):
        dependency = f"{group}:{artifact}"
        if version:
            dependency += ":" + version
        dependencies.append(dependency)
    return dependencies


def build_graph(config, config_directory):
    """Строит граф зависимостей с помощью BFS."""
    test_mode = config["test_mode"]
    root = config["package_name"]
    substring = config["filter_substring"]

    if substring and substring in root:
        return {}

    if test_mode:
        path = Path(config["repository"])
        if not path.is_absolute():
            path = config_directory / path
        repository = load_test_repository(path)
        if root not in repository:
            raise ValueError(f"Пакет {root} отсутствует в тестовом репозитории")
    else:
        root += ":" + config["version"]
        repository = None

    graph = {root: []}
    queue = deque([(root, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= config["max_depth"]:
            continue

        dependencies = get_node_dependencies(node, config, test_mode, repository)
        for dependency in dependencies:
            name = dependency if test_mode else ":".join(dependency.split(":")[:2])
            if substring and substring in name:
                continue
            if dependency not in graph[node]:
                graph[node].append(dependency)
            if dependency not in graph:
                graph[dependency] = []
                queue.append((dependency, depth + 1))
    return graph


def get_load_order(graph):
    """Возвращает порядок загрузки."""
    remaining = {package: len(dependencies) for package, dependencies in graph.items()}
    dependents = {package: [] for package in graph}
    for package, dependencies in graph.items():
        for dependency in dependencies:
            dependents[dependency].append(package)

    queue = deque(package for package in graph if remaining[package] == 0)
    order = []
    while queue:
        package = queue.popleft()
        order.append(package)
        for dependent in dependents[package]:
            remaining[dependent] -= 1
            if remaining[dependent] == 0:
                queue.append(dependent)
    if len(order) != len(graph):
        raise ValueError("Граф содержит цикл: порядок загрузки определить невозможно")
    return order


def to_d2(graph):
    """Преобразует граф в формат D2."""
    identifiers = {}
    lines = []
    for index, package in enumerate(graph):
        identifier = f"n{index}"
        identifiers[package] = identifier
        label = json.dumps(package, ensure_ascii=False)
        lines.append(f"{identifier}: {label}")
    for package, dependencies in graph.items():
        for dependency in dependencies:
            lines.append(f"{identifiers[package]} -> {identifiers[dependency]}")
    return "\n".join(lines)
