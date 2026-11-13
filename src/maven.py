import re
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen
from xml.etree import ElementTree


def read_pom(config, config_directory):
    if config["test_mode"]:
        path = Path(config["repository"])
        if not path.is_absolute():
            path = config_directory / path
        try:
            return path.read_bytes()
        except OSError as error:
            raise ValueError(f"Не удалось прочитать тестовый POM: {error}") from error
    group, artifact = config["package_name"].split(":")
    version = config["version"]
    parts = group.split(".") + [artifact, version, f"{artifact}-{version}.pom"]
    address = config["repository"].rstrip("/") + "/"
    address += "/".join(quote(part, safe="") for part in parts)
    try:
        with urlopen(address, timeout=15) as response:
            return response.read()
    except (OSError, ValueError) as error:
        raise ValueError(f"Не удалось загрузить POM {address}: {error}") from error


def resolve_properties(value, properties):
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


def parse_dependencies(content, package_name, version):
    try:
        project = ElementTree.fromstring(content)
    except ElementTree.ParseError as error:
        raise ValueError(f"Некорректный XML в POM: {error}") from error
    for element in project.iter():
        element.tag = element.tag.split("}")[-1]
    if project.tag != "project":
        raise ValueError("В POM отсутствует корневой элемент project")

    group, artifact = package_name.split(":")
    properties = {}
    for element in project.findall("./properties/*"):
        properties[element.tag] = (element.text or "").strip()
    for name, value in (("groupId", group), ("artifactId", artifact), ("version", version)):
        properties["project." + name] = value
        properties["pom." + name] = value

    dependencies = []
    for dependency in project.findall("./dependencies/dependency"):
        values = []
        for name in ("groupId", "artifactId", "version"):
            value = dependency.findtext(name, default="").strip()
            values.append(resolve_properties(value, properties))
        if not values[0] or not values[1]:
            raise ValueError("У зависимости в POM отсутствует groupId или artifactId")
        dependencies.append(tuple(values))
    return dependencies


def get_dependencies(config, config_directory):
    content = read_pom(config, config_directory)
    return parse_dependencies(content, config["package_name"], config["version"])
