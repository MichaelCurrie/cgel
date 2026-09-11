"""CLI behaviour, plus the encoding/newline invariants the package promises."""

from __future__ import annotations

import json

import pytest

from cgel_json_converter.cli import main
from cgel_json_converter.tree_validation import validate_cgel_files


def test_writes_valid_jsonld_to_a_file(demo_cgel, tmp_path):
    out = tmp_path / 'out.json'
    assert main([str(demo_cgel), '-o', str(out)]) == 0

    doc = json.loads(out.read_text(encoding='utf-8'))
    assert doc['@type'] == 'Corpus'
    assert len(doc['trees']) == 2


def test_output_is_utf8_with_lf_endings(demo_cgel, tmp_path):
    out = tmp_path / 'out.json'
    main([str(demo_cgel), '-o', str(out)])

    raw = out.read_bytes()
    assert b'\r\n' not in raw, 'output must use LF, even on Windows'
    assert raw.endswith(b'\n')
    raw.decode('utf-8')  # raises if we ever wrote cp1252


def test_non_ascii_survives_the_round_trip(tmp_path):
    src = tmp_path / 'unicode.cgel'
    src.write_text(
        '# sent_id = u1\n'
        '# sent = café naïve — 中文\n'
        '(Nom\n'
        '    :Head (N :t "café")\n'
        '    :Mod (N :t "naïve")\n'
        '    :Mod (N :t "—")\n'
        '    :Mod (N :t "中文"))\n',
        encoding='utf-8', newline='')

    out = tmp_path / 'out.json'
    assert main([str(src), '-o', str(out), '--round-trip']) == 0

    doc = json.loads(out.read_text(encoding='utf-8'))
    texts = [n['text'] for n in _terminals(doc['trees'][0]['root'])]
    assert texts == ['café', 'naïve', '—', '中文']
    # ensure_ascii=False keeps them literal in the file, not \uXXXX-escaped
    assert 'café' in out.read_text(encoding='utf-8')


def test_crlf_input_parses_identically(demo_cgel, tmp_path):
    crlf = tmp_path / 'crlf.cgel'
    crlf.write_bytes(demo_cgel.read_bytes().replace(b'\n', b'\r\n'))

    lf_out, crlf_out = tmp_path / 'lf.json', tmp_path / 'crlf.json'
    assert main([str(demo_cgel), '-o', str(lf_out)]) == 0
    assert main([str(crlf), '-o', str(crlf_out)]) == 0

    lf_doc = json.loads(lf_out.read_text(encoding='utf-8'))
    crlf_doc = json.loads(crlf_out.read_text(encoding='utf-8'))
    # the documents may differ only in the input filename
    assert _canonical(lf_doc, 'demo_input') == _canonical(crlf_doc, 'crlf')


def test_round_trip_and_tree_validation_pass(demo_cgel, tmp_path):
    assert main([str(demo_cgel), '-o', str(tmp_path / 'out.json'),
                 '--round-trip', '--validate-trees']) == 0


def test_demo_trees_are_well_formed(demo_cgel):
    report = validate_cgel_files([demo_cgel])
    assert report.ok, str(report)


def test_stdout_mode_emits_only_json(demo_cgel, capsys):
    assert main([str(demo_cgel)]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)['@type'] == 'Corpus'


def test_missing_file_is_an_error(tmp_path):
    with pytest.raises(SystemExit):
        main([str(tmp_path / 'nope.cgel')])


def test_glob_expands_on_the_cli(demo_cgel, tmp_path):
    """PowerShell does not expand `*.cgel`; the CLI has to."""
    (tmp_path / 'a.cgel').write_bytes(demo_cgel.read_bytes())
    (tmp_path / 'b.cgel').write_bytes(demo_cgel.read_bytes())
    out = tmp_path / 'out.json'
    assert main([str(tmp_path / '*.cgel'), '-o', str(out)]) == 0
    doc = json.loads(out.read_text(encoding='utf-8'))
    assert len(doc['trees']) == 4


def test_indent_zero_is_one_line(demo_cgel, tmp_path):
    out = tmp_path / 'compact.json'
    main([str(demo_cgel), '-o', str(out), '--indent', '0'])
    assert out.read_text(encoding='utf-8').count('\n') == 1


# ------------------------------------------------------------------- helpers

def _terminals(node):
    if 'text' in node:
        yield node
    for c in node.get('children', []):
        yield from _terminals(c)


def _canonical(doc, stem):
    """Drop the two fields that legitimately depend on the input filename."""
    doc = json.loads(json.dumps(doc).replace(f'urn:cgel:{stem}:', 'urn:cgel:STEM:'))
    for tree in doc['trees']:
        tree.pop('source', None)
    return doc
