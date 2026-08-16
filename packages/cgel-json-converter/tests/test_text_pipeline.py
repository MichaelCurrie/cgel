"""The plain-text -> JSON-LD path.

Stanza downloads ~500 MB of EWT models on first use, so these tests are opt-in:

    CGEL_TEST_STANZA=1 uv run pytest tests/test_text_pipeline.py
"""

from __future__ import annotations

import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get('CGEL_TEST_STANZA') != '1',
    reason='set CGEL_TEST_STANZA=1 to exercise the Stanza pipeline (downloads models)')


def test_text_file_becomes_valid_jsonld(demo_txt, tmp_path):
    from cgel_json_converter.cli import main

    out = tmp_path / 'out.json'
    assert main([str(demo_txt), '--from', 'text', '-o', str(out),
                 '--work-dir', str(tmp_path / 'work')]) == 0

    doc = json.loads(out.read_text(encoding='utf-8'))
    assert len(doc['trees']) == 2
    # trees are attributed to the .txt the user named, not the generated .cgel
    assert all(t['source'].endswith('demo_input.txt') for t in doc['trees'])
    assert doc['trees'][0]['root']['category']


def test_intermediates_are_kept_when_asked(demo_txt, tmp_path):
    from cgel_json_converter.cli import main

    work = tmp_path / 'work'
    main([str(demo_txt), '--from', 'text', '-o', str(tmp_path / 'out.json'),
          '--work-dir', str(work)])

    produced = {p.name for p in work.iterdir()}
    assert 'demo_input.cgel' in produced
    assert 'demo_input.ud.conllu' in produced


def test_text_to_cgel_api(tmp_path):
    from cgel_json_converter import read_trees, text_to_cgel

    path = text_to_cgel('The dog barked at the mailman.', tmp_path)
    trees = read_trees(path)
    assert len(trees) == 1
    assert 'dog' in trees[0].sentence()
