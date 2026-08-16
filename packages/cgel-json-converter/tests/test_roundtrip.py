"""The JSON-LD mapping must be lossless: JSON -> PENMAN -> byte-identical .cgel."""

from __future__ import annotations

from cgel_json_converter import jsonld_to_cgel, read_trees, round_trip


def test_round_trip_reports_no_failures(demo_doc, demo_cgel):
    assert round_trip(demo_doc, [demo_cgel]) == 0


def test_each_tree_reserializes_byte_identically(demo_doc, demo_cgel):
    originals = [t.draw(include_metadata=True) for t in read_trees(demo_cgel)]
    assert len(originals) == len(demo_doc['trees'])
    for original, tree in zip(originals, demo_doc['trees']):
        assert jsonld_to_cgel(tree) == original


def test_round_trip_notices_a_corrupted_document(demo_doc, demo_cgel):
    """Guard against the check silently passing on anything."""
    import copy

    broken = copy.deepcopy(demo_doc)
    broken['trees'][0]['root']['category'] = 'NotAClause'
    assert round_trip(broken, [demo_cgel]) == 1
