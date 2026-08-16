"""Locations of the data files shipped inside the package.

Both files live under ``cgel_json_converter/data/`` and are declared as package
data in ``pyproject.toml``, so they travel with the wheel. Nothing here reaches
outside the package directory -- that is what makes the folder copyable into
another repository as a unit.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

DATA_DIR = Path(str(files('cgel_json_converter').joinpath('data')))

#: JSON Schema (draft 2020-12) that converter output is validated against.
SCHEMA_PATH = DATA_DIR / 'cgel-jsonld.schema.json'

#: DepEdit rewrite rules turning Universal Dependencies into CGEL relations.
DEPEDIT_CONFIG_PATH = DATA_DIR / 'ud-to-cgel.ini'
