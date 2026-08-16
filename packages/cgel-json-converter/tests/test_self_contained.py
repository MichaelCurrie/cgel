"""The package must be copyable into another repository as a unit.

That means no module may import anything that is neither the standard library,
a declared runtime dependency, nor a sibling inside this package.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

import cgel_json_converter

PKG_DIR = Path(cgel_json_converter.__file__).resolve().parent

#: Third-party roots declared in pyproject.toml's [project.dependencies].
DECLARED = {'conllu', 'depedit', 'jsonschema', 'pylatexenc', 'stanza'}

ALLOWED = DECLARED | set(sys.stdlib_module_names) | {'cgel_json_converter'}

MODULES = sorted(PKG_DIR.glob('*.py'))


def test_there_are_modules_to_check():
    assert MODULES, f'no modules found under {PKG_DIR.as_posix()}'


@pytest.mark.parametrize('path', MODULES, ids=lambda p: p.name)
def test_no_imports_from_outside_the_package(path: Path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split('.')[0]
                assert root in ALLOWED, f'{path.name} imports undeclared {root!r}'
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # `from . import x` is fine; `from .. import x` escapes the package.
                assert node.level == 1, f'{path.name} imports above the package root'
            elif node.module:
                root = node.module.split('.')[0]
                assert root in ALLOWED, f'{path.name} imports undeclared {root!r}'


@pytest.mark.parametrize('path', MODULES, ids=lambda p: p.name)
def test_no_bare_sibling_imports(path: Path):
    """`import cgel` would resolve to the *other* repo's module if one exists."""
    siblings = {p.stem for p in MODULES} - {'__init__'}
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split('.')[0] not in siblings, (
                    f'{path.name}: `import {alias.name}` must be relative')
        elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
            assert node.module.split('.')[0] not in siblings, (
                f'{path.name}: `from {node.module} import ...` must be relative')


def test_data_files_ship_with_the_package():
    from cgel_json_converter import DEPEDIT_CONFIG_PATH, SCHEMA_PATH

    for p in (SCHEMA_PATH, DEPEDIT_CONFIG_PATH):
        assert p.is_file(), f'missing packaged data file: {p.as_posix()}'
        assert PKG_DIR in p.resolve().parents, f'{p.as_posix()} lives outside the package'
