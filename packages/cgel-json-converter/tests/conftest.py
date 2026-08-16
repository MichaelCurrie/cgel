from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEMO_CGEL = PACKAGE_ROOT / 'demo_input.cgel'
DEMO_TXT = PACKAGE_ROOT / 'demo_input.txt'


@pytest.fixture(scope='session')
def demo_cgel() -> Path:
    return DEMO_CGEL


@pytest.fixture(scope='session')
def demo_txt() -> Path:
    return DEMO_TXT


@pytest.fixture(scope='session')
def demo_doc(demo_cgel: Path) -> dict:
    from cgel_json_converter import convert
    return convert([demo_cgel])
