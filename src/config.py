import re
from pathlib import Path
from urllib.parse import urlsplit

import yaml

PARAMETERS = (
    "package_name",
    "repository",
    "test_mode",
    "version",
    "max_depth",
    "filter_substring",
)


def validate_config(config, config_directory):
    errors = []
    for name in PARAMETERS:
        if name not in config:
            errors.append(f"{name}: параметр отсутствует")
    for name in ("package_name", "repository", "version"):
        if name in config:
            value = config[name]
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{name}: ожидается непустая строка")
    package = config.get("package_name")
    if isinstance(package, str) and package.strip():  
        if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*:[A-Za-z0-9_][A-Za-z0-9_.-]*", package):
            errors.append("package_name: ожидается имя Maven-пакета groupId:artifactId")
    version = config.get("version")
    if isinstance(version, str) and version.strip():  
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.+-]*", version):
            errors.append("version: недопустимый номер версии Maven-пакета")
    if "test_mode" in config and type(config["test_mode"]) is not bool:
        errors.append("test_mode: ожидается true или false")
    if "max_depth" in config:
        value = config["max_depth"]
        if type(value) is not int or value < 0:
            errors.append("max_depth: ожидается целое число не меньше нуля")
    if "filter_substring" in config:
        if not isinstance(config["filter_substring"], str):
            errors.append("filter_substring: ожидается строка")

    repository = config.get("repository")
    test_mode = config.get("test_mode")
    if isinstance(repository, str) and repository.strip():
        if test_mode is True:
            path = Path(repository)
            if not path.is_absolute():
                path = config_directory / path
            try:
                with path.open("rb"):
                    pass
            except (OSError, ValueError):
                errors.append("repository: файл тестового репозитория недоступен")
        elif test_mode is False:
            try:
                url = urlsplit(repository)
                valid = (
                    url.scheme in ("http", "https")
                    and bool(url.hostname)
                    and not any(char.isspace() for char in repository)
                )
                url.port
            except ValueError:
                valid = False
            if not valid:
                errors.append("repository: ожидается URL с протоколом http или https")
    if errors:
        raise ValueError("\n".join(errors))


def load_config(filename):
    path = Path(filename)
    try:
        with path.open(encoding="utf-8") as file:
            config = yaml.safe_load(file)
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Не удалось прочитать конфигурацию: {error}") from error
    except yaml.YAMLError as error:
        raise ValueError(f"Ошибка YAML: {error}") from error
    if not isinstance(config, dict):
        raise ValueError("Конфигурация должна содержать параметры в формате ключ-значение")
    validate_config(config, path.resolve().parent)
    return {name: config[name] for name in PARAMETERS}
