from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from aura2.pipeline.spec import ExperimentSpec


def slugify(text: str) -> str:
    replacements = {"%": "pct", "+": "plus", "-": "minus", " ": "_", "/": "_"}
    for k, v in replacements.items():
        text = text.replace(k, v)
    return "".join(c for c in text.lower() if c.isalnum() or c == "_")


class Option:
    def __init__(self, name: str, IS_DEFAULT: bool = False) -> None:
        self.name = name
        self.IS_DEFAULT = IS_DEFAULT


@dataclass
class Variable:
    name: str
    options: list[Option]

    def __post_init__(self) -> None:
        defaults = [o for o in self.options if o.IS_DEFAULT]
        assert len(defaults) == 1, f"{self.name}: need exactly one default option"
        names = [o.name for o in self.options]
        assert len(set(names)) == len(names), f"{self.name}: option names not unique"

    @property
    def default_option(self) -> str:
        return next(o.name for o in self.options if o.IS_DEFAULT)

    @property
    def non_default_options(self) -> list[str]:
        return [o.name for o in self.options if not o.IS_DEFAULT]


@dataclass
class DefinitionDict:
    case_names: list[str]
    modifications: list[Variable]


def spec_id(case_name: str, modification: tuple[str, str] | None) -> str:
    if modification is None:
        return f"{case_name}__default"
    var, opt = modification
    return f"{case_name}__{slugify(var)}__{slugify(opt)}"


def enumerate_specs(defn: DefinitionDict) -> list[ExperimentSpec]:
    baseline = [
        ExperimentSpec(id=spec_id(case, None), case_name=case, modification=None)
        for case in defn.case_names
    ]
    modified = [
        ExperimentSpec(
            id=spec_id(case, (var.name, option)),
            case_name=case,
            modification=(var.name, option),
        )
        for var in defn.modifications
        for case, option in product(defn.case_names, var.non_default_options)
    ]
    return baseline + modified
