"""Convert CGEL constituency trees, or plain English text, to annotated JSON-LD.

Self-contained: every module, the JSON Schema and the DepEdit rule file live
inside this package, and nothing imports from outside it. The directory can be
copied wholesale into another repository.

Typical use::

    from pathlib import Path
    from cgel_json_converter import convert, dumps, validate

    doc = convert([Path('demo_input.cgel')])
    assert validate(doc) == 0
    print(dumps(doc))

The raw-text entry points (:func:`text_to_cgel`, :func:`file_to_cgel`) are
imported lazily on attribute access, because they pull in Stanza and torch.
"""

from __future__ import annotations

from typing import Any

from .cgel2jsonld import (
    CONTEXT,
    NS,
    convert,
    dumps,
    jsonld_to_cgel,
    read_trees,
    round_trip,
    tree_to_jsonld,
    validate,
    write,
)
from .resources import DEPEDIT_CONFIG_PATH, SCHEMA_PATH
from .validate import Report, validate_cgel_files

__version__ = '0.1.0'

__all__ = [
    'CONTEXT',
    'DEPEDIT_CONFIG_PATH',
    'NS',
    'Report',
    'SCHEMA_PATH',
    '__version__',
    'convert',
    'dumps',
    'file_to_cgel',
    'jsonld_to_cgel',
    'read_trees',
    'round_trip',
    'text_to_cgel',
    'tree_to_jsonld',
    'ud_to_cgel',
    'validate',
    'validate_cgel_files',
    'write',
]

#: Names served lazily, so `import cgel_json_converter` stays cheap.
_LAZY = {
    'text_to_cgel': ('.txt2cgel', 'text_to_cgel'),
    'file_to_cgel': ('.txt2cgel', 'file_to_cgel'),
    'ud_to_cgel': ('.ud2cgel', 'convert'),
}


def __getattr__(name: str) -> Any:
    try:
        module, attr = _LAZY[name]
    except KeyError:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}') from None
    from importlib import import_module
    return getattr(import_module(module, __name__), attr)


def __dir__() -> list[str]:
    return sorted(__all__)
