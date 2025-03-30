from typing import Any

import yaml


def __literal_string_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def __list_set_representer(dumper: yaml.Dumper, data: set[str]) -> yaml.SequenceNode:
    return dumper.represent_list(list(data))


def __list_tuple_representer(dumper: yaml.Dumper, data: tuple[str]) -> yaml.SequenceNode:
    return dumper.represent_list(list(data))


yaml.add_representer(str, __literal_string_representer)
yaml.add_representer(set, __list_set_representer)
yaml.add_representer(tuple, __list_tuple_representer)


def dumps(obj: Any) -> str:
    """Serialize obj as yaml."""
    return yaml.dump(obj, default_flow_style=False, allow_unicode=True)
