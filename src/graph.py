import re
from collections import deque
from pathlib import Path

import yaml

from maven import get_dependencies


def load_test_repository(filename):
    try:
        with Path(filename).open(encoding="utf-8") as file:
            repository = yaml.safe_load(file)
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"Не удалось прочитать тестовый репозиторий: {error}") from error
    if not isinstance(repository, dict):
        raise ValueError("Тестовый репозиторий должен содержать пары пакет: список зависимостей")
    for name, dependencies in repository.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Z]+", name):
            raise ValueError("Имена тестовых пакетов должны состоять из больших латинских букв")
        if not isinstance(dependencies, list):
            raise ValueError(f"Зависимости пакета {name} должны быть списком")
        for dependency in dependencies:
            if not isinstance(dependency, str) or dependency not in repository:
                raise ValueError(f"Неизвестная зависимость {dependency} у пакета {name}")
    return repository


def build_graph(config, config_directory):
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

    graph = {root: []}
    queue = deque([(root, 0)])
    while queue:
        node, depth = queue.popleft()
        if depth >= config["max_depth"]:
            continue
        if test_mode:
            dependencies = repository[node]
        else:
            parts = node.split(":")
            if len(parts) != 3 or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", parts[2]):
                raise ValueError(f"Для анализа пакета {node} в POM не указана конкретная версия")
            package_config = config.copy()
            package_config["package_name"] = ":".join(parts[:2])
            package_config["version"] = parts[2]
            dependencies = []
            for group, artifact, version in get_dependencies(package_config):
                dependency = f"{group}:{artifact}"
                if version:
                    dependency += ":" + version
                dependencies.append(dependency)
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
