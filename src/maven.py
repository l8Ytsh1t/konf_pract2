"""Модуль для скачивания и разбора Maven POM."""
import re
from urllib.parse import quote
from urllib.request import urlopen
from xml.etree import ElementTree

TIMEOUT_SECONDS = 15


def read_pom(config):
    """Скачивает POM-файл и возвращает его содержимое."""
    group, artifact = config["package_name"].split(":")
    version = config["version"]
    parts = group.split(".") + [artifact, version, f"{artifact}-{version}.pom"]
    address = config["repository"].rstrip("/") + "/"
    address += "/".join(quote(part, safe="") for part in parts)
    
    try:
        with urlopen(address, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except (OSError, ValueError) as error:
        raise ValueError(f"Не удалось загрузить POM {address}: {error}") from error


def resolve_properties(value, properties):
    """Подставляет переменные ${...} в строку."""
    for _ in range(len(properties) + 1):
        updated = re.sub(
            r"\$\{([^}]+)\}",
            lambda match: properties.get(match.group(1), match.group(0)),
            value,
        )
        if updated == value:
            return value
        value = updated
    raise ValueError("Циклические свойства в POM")


def _extract_properties(project, group, artifact, version):
    """Собирает свойства из POM и добавляет стандартные."""
    properties = {}
    for element in project.findall("./properties/*"):
        properties[element.tag] = (element.text or "").strip()
    for name, val in (("groupId", group), ("artifactId", artifact), ("version", version)):
        properties["project." + name] = val
        properties["pom." + name] = val
    return properties


def _parse_single_dependency(dependency, properties):
    """Парсит одну зависимость."""
    values = []
    for name in ("groupId", "artifactId", "version"):
        value = dependency.findtext(name, default="").strip()
        values.append(resolve_properties(value, properties))
    if not values[0] or not values[1]:
        raise ValueError("У зависимости в POM отсутствует groupId или artifactId")
    return tuple(values)


def parse_dependencies(content, package_name, version):
    """Разбирает XML и возвращает список зависимостей."""
    try:
        project = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError(f"Некорректный XML в POM: {error}") from error
        
    for element in project.iter():
        element.tag = element.tag.split("}")[-1]
    if project.tag != "project":
        raise ValueError("В POM отсутствует корневой элемент project")

    group, artifact = package_name.split(":")
    properties = _extract_properties(project, group, artifact, version)

    dependencies = []
    for dependency in project.findall("./dependencies/dependency"):
        dependencies.append(_parse_single_dependency(dependency, properties))
    return dependencies


def get_dependencies(config):
    """Возвращает прямые зависимости пакета."""
    content = read_pom(config)
    return parse_dependencies(content, config["package_name"], config["version"])