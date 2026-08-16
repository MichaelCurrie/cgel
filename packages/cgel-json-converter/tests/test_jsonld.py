"""Conversion output: shape, annotation content, and schema conformance."""

from __future__ import annotations

import json

from cgel_json_converter import dumps, validate
from cgel_json_converter.cgel2jsonld import CONTEXT


def nodes(n: dict):
    """Yield a node and all its descendants."""
    yield n
    for c in n.get('children', []):
        yield from nodes(c)


def test_validates_against_schema(demo_doc):
    assert validate(demo_doc) == 0


def test_corpus_envelope(demo_doc):
    assert demo_doc['@type'] == 'Corpus'
    assert demo_doc['@context'] == CONTEXT
    assert len(demo_doc['trees']) == 2


def test_tree_headers(demo_doc):
    first = demo_doc['trees'][0]
    assert first['@type'] == 'Tree'
    assert first['sentId'] == 'Tree TheFutureOfLinguistics-0'
    assert first['sentNum'] == 1
    assert first['text'].startswith('The #futureoflinguistics')
    # metadata stays authoritative and ordered
    assert [e['key'] for e in first['metadata']] == ['sent_id', 'sent_num', 'text', 'sent']


def test_source_is_posix(demo_doc):
    """No Windows backslashes leak into the document."""
    for tree in demo_doc['trees']:
        assert '\\' not in tree['source']
        assert tree['source'].endswith('demo_input.cgel')


def test_hierarchy_mirrors_indentation(demo_doc):
    root = demo_doc['trees'][0]['root']
    assert root['category'] == 'Clause'
    assert 'function' not in root, 'the root has no grammatical function'
    subj = root['children'][0]
    assert (subj['function'], subj['category']) == ('Subj', 'NP')


def test_terminal_annotations(demo_doc):
    all_nodes = list(nodes(demo_doc['trees'][0]['root']))
    by_text = {n['text']: n for n in all_nodes if 'text' in n}

    assert by_text['is']['lemma'] == 'be'
    assert by_text['is']['xpos'] == 'VBZ'
    assert by_text['aided']['postPunct'] == [',']
    assert by_text['world']['postPunct'] == ['.']

    # positions number the terminals left to right, starting at 1
    positions = [n['position'] for n in all_nodes if 'position' in n]
    assert positions == list(range(1, len(positions) + 1))


def test_gap_resolves_to_its_antecedent(demo_doc):
    all_nodes = list(nodes(demo_doc['trees'][1]['root']))
    gaps = [n for n in all_nodes if n['category'] == 'GAP']
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap['index'] == 'x'

    antecedent_id = gap['antecedent']['@id']
    antecedent = next(n for n in all_nodes if n['@id'] == antecedent_id)
    assert antecedent['category'] == 'Nom'
    assert antecedent['index'] == 'x'
    assert antecedent is not gap


def test_node_ids_are_unique_and_scoped_to_their_tree(demo_doc):
    seen = set()
    for tree in demo_doc['trees']:
        for n in nodes(tree['root']):
            assert n['@id'] not in seen
            assert n['@id'].startswith(tree['@id'] + '#n')
            seen.add(n['@id'])


def test_dumps_is_valid_json_and_keeps_unicode(demo_doc):
    text = dumps(demo_doc, indent=2)
    assert json.loads(text) == demo_doc
    assert dumps(demo_doc, indent=0).count('\n') == 0
