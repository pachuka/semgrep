"""
Parsers for poetry.lock and pyproject.toml files
I could not find any comprehensive description of this format online, I just looked at examples
If you find any sort of spec, please link it here
Here's the docs for poetry: https://python-poetry.org/docs/
"""
from pathlib import Path
from typing import List
from typing import Optional

from semdep.external.parsy import any_char
from semdep.external.parsy import eof
from semdep.external.parsy import regex
from semdep.external.parsy import string
from semdep.parsers.util import mark_line
from semdep.parsers.util import pair
from semdep.parsers.util import ParserName
from semdep.parsers.util import safe_path_parse
from semdep.parsers.util import transitivity
from semdep.parsers.util import upto
from semgrep.semgrep_interfaces.semgrep_output_v1 import Ecosystem
from semgrep.semgrep_interfaces.semgrep_output_v1 import FoundDependency
from semgrep.semgrep_interfaces.semgrep_output_v1 import Pypi

# These use [until] instead of [upto] because [upto] only works on single characters
# and [upto] works on arbitrary parsers (this makes it slower though)
# We don't care about the contents of any list or object values right now

# Using ]\n allows us to avoid issues with closing brackets inside strings
# Examples:
# [foo, bar]
# [
#   foo,
#   bar
# ]
list_value = (
    string("[")
    >> any_char.until(string("]") << (string("\n") | eof)).result("")
    << string("]")
)

# Examples:
# {version = "*", optional = true, markers = "python_full_version <= \"3.11.0a6\" and extra == \"toml\""}
object_value = (
    string("{")
    >> any_char.until(string("}") << (string("\n") | eof)).result("")
    << string("}")
)

# Examples:
# "foo"
# "foo[bar]"
quoted_value = (
    string('"')
    >> any_char.until(string('"\n')).concat().map(lambda x: x.strip('"'))
    << string('"')
)

# Examples:
# foo
plain_value = upto("\n")

# A value in a key-value pair.
value = list_value | object_value | quoted_value | plain_value


# A key-value pair.
# Examples:
# foo = bar

# foo = [
#     bar, baz
# ]
key_value = pair(regex(r"([^\s=]+)\s*=\s*", flags=0, group=1), value)

# A poetry dependency
# Example:
# [[package]]
# name = "factory-boy"
# version = "3.2.1"
# description = "A versatile test fixtures replacement based on thoughtbot's factory_bot for Ruby."
# category = "main"
# optional = false
# python-versions = ">=3.6"
poetry_dep = mark_line(
    string("[[package]]\n") >> key_value.sep_by(string("\n")).map(lambda x: dict(x))
)

# Poetry Source which we ignore
# Example:
# [[tool.poetry.source]]
# name = "semgrep"
# url = "https://artifact.semgrep.com/"
# secondary = False
poetry_source_extra = (
    string("[[") >> upto("]") << string("]]\n") >> key_value.sep_by(string("\n"))
).map(lambda _: None)

# Extra data from a dependency, which we just treat as standalone data and ignore
# Example:
# [package.extras]
# dev = ["coverage", "django", "flake8", "isort", "pillow", "sqlalchemy", "mongoengine", "wheel (>=0.32.0)", "tox", "zest.releaser"]
# doc = ["sphinx", "sphinx-rtd-theme", "sphinxcontrib-spelling"]
poetry_dep_extra = (string("[") >> upto("]") << string("]\n")) >> key_value.sep_by(
    string("\n")
).map(lambda _: None)


comment = regex(r" *#([^\n]*)", flags=0, group=1)

# A whole poetry file
poetry = (
    comment.many()
    >> string("\n").many()
    >> (poetry_dep | poetry_dep_extra | (string("package = []").result(None)))
    .sep_by(string("\n\n"))
    .map(lambda xs: [x for x in xs if x])
    << string("\n").optional()
)


# Direct dependencies listed in a pyproject.toml file
# Example:
# [tool.poetry.dependencies]
# python = "^3.10"
# faker = "^13.11.0"
manifest_deps = string("[tool.poetry.dependencies]\n") >> key_value.map(
    lambda x: x[0]
).sep_by(string("\n"))

# A whole pyproject.toml file. We only about parsing the manifest_deps
manifest = (manifest_deps | poetry_dep_extra | poetry_source_extra).sep_by(
    string("\n").times(min=1, max=float("inf"))
).map(lambda xs: {y for x in xs if x for y in x}) << string("\n").optional()


def parse_poetry(
    lockfile_path: Path, manifest_path: Optional[Path]
) -> List[FoundDependency]:
    deps = safe_path_parse(lockfile_path, poetry, ParserName.poetry_lock)
    if not deps:
        return []
    manifest_deps = safe_path_parse(manifest_path, manifest, ParserName.pyproject_toml)

    # According to PEP 426: pypi distributions are case insensitive and consider hyphens and underscores to be equivalent
    sanitized_manifest_deps = (
        {dep.lower().replace("-", "_") for dep in manifest_deps}
        if manifest_deps
        else manifest_deps
    )

    output = []
    for line_number, dep in deps:
        if "name" not in dep or "version" not in dep:
            continue
        output.append(
            FoundDependency(
                package=dep["name"],
                version=dep["version"],
                ecosystem=Ecosystem(Pypi()),
                allowed_hashes={},
                transitivity=transitivity(
                    sanitized_manifest_deps, [dep["name"].lower().replace("-", "_")]
                ),
                line_number=line_number,
            )
        )
    return output
