#!/usr/bin/env python3
"""Convert CGEL trees to JSON-LD (and back, for verification).

Each level of indentation in the .cgel source becomes one level of nesting
under `children`, so the JSON mirrors the constituency hierarchy directly:

    (Clause                             {"category": "Clause", "children": [
        :Subj (NP                         {"function": "Subj", "category": "NP", "children": [
            :Head (Nom                      {"function": "Head", "category": "Nom", "children": [
                :Head (N :t "dog"))))         {"function": "Head", "category": "N", "text": "dog"} ...

The mapping is lossless: `round_trip()` re-serializes the JSON back to PENMAN
notation via cgel.Node.__str__ and asserts it is byte-identical to the input.

Output validates against the packaged schema, `data/cgel-jsonld.schema.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote

from . import cgel
from .io_utils import log, open_read, posix, write_text
from .resources import SCHEMA_PATH

NS = 'https://nert-nlp.github.io/cgel/ns#'

#: Emitted inline into every document so the output is self-contained.
CONTEXT: dict[str, Any] = {
    '@version': 1.1,
    '@vocab': NS,
    'cgel': NS,
    'Corpus': 'cgel:Corpus',
    'Tree': 'cgel:Tree',
    'Node': 'cgel:Node',
    # Order is syntactically meaningful throughout, so these are @lists rather
    # than unordered RDF sets.
    'trees': {'@id': 'cgel:tree', '@container': '@list'},
    'children': {'@id': 'cgel:child', '@container': '@list'},
    'metadata': {'@id': 'cgel:metadata', '@container': '@list'},
    'prePunct': {'@id': 'cgel:prePunct', '@container': '@list'},
    'postPunct': {'@id': 'cgel:postPunct', '@container': '@list'},
    'subtokens': {'@id': 'cgel:subtoken', '@container': '@list'},
    'antecedent': {'@id': 'cgel:antecedent', '@type': '@id'},
    'root': {'@id': 'cgel:root'},
    'source': {'@id': 'cgel:source'},
    'sentNum': {'@id': 'cgel:sentNum', '@type': 'http://www.w3.org/2001/XMLSchema#integer'},
    'position': {'@id': 'cgel:position', '@type': 'http://www.w3.org/2001/XMLSchema#integer'},
}


# ---------------------------------------------------------------- cgel -> json

def tree_iri(tree: cgel.Tree, source: Path, index: int) -> str:
    """Stable IRI for a tree: its sent_id if it has one, else its position in the file."""
    ident = tree.metadata.get('sent_id') or tree.metadata.get('sent_num') or str(index + 1)
    return f'urn:cgel:{quote(source.stem, safe="")}:{quote(str(ident), safe="")}'


def node_to_jsonld(tree: cgel.Tree, i: int, base: str, counter: list[int],
                   position: list[int], ids: dict[int, str]) -> dict[str, Any]:
    """Recursively convert token `i` of `tree`. `counter`/`position` are mutable cells."""
    node: cgel.Node = tree.tokens[i]

    nid = f'{base}#n{counter[0]}'
    counter[0] += 1
    ids[i] = nid

    out: dict[str, Any] = {'@id': nid, '@type': 'Node'}

    # `deprel` is None only at the root.
    if node.deprel:
        out['function'] = node.deprel
    out['category'] = node.constituent
    if node.label:
        out['index'] = node.label

    if node.text is not None:
        out['text'] = node.text
        position[0] += 1
        out['position'] = position[0]

    # `_lemma` rather than the `lemma` property: only lemmas written explicitly
    # as `:l` in the source belong here, otherwise round-tripping would invent them.
    if node._lemma:
        out['lemma'] = node._lemma
    if node.xpos:
        out['xpos'] = node.xpos
    # `:correct ""` deletes a spurious token, so test against None, not falsiness.
    if node.correct is not None:
        out['correct'] = node.correct
    if node.note:
        out['note'] = node.note

    if node.prepunct:
        out['prePunct'] = list(node.prepunct)
    if node.postpunct:
        out['postPunct'] = list(node.postpunct)
    if node.substrings:
        out['subtokens'] = [{'kind': k.lstrip(':'), 'value': v} for k, v in node.substrings]

    # cgel.Tree.draw_rec does not descend into gaps; neither do we.
    if node.constituent != 'GAP':
        children = [node_to_jsonld(tree, c, base, counter, position, ids)
                    for c in tree.children[i]]
        if children:
            out['children'] = children

    return out


def resolve_antecedents(tree: cgel.Tree, root: dict[str, Any], ids: dict[int, str]) -> None:
    """Point each gap at the node bearing the same coindexation variable.

    cgel.Tree.labels records antecedents only (gaps are deliberately not unified
    with them), which is exactly the lookup table we want.
    """
    def walk(n: dict[str, Any]) -> None:
        if n.get('category') == 'GAP' and 'index' in n:
            antecedent = tree.labels.get(n['index'])
            if antecedent is not None and antecedent in ids:
                n['antecedent'] = {'@id': ids[antecedent]}
        for c in n.get('children', []):
            walk(c)
    walk(root)


def tree_to_jsonld(tree: cgel.Tree, source: Path, index: int) -> dict[str, Any]:
    base = tree_iri(tree, source, index)
    ids: dict[int, str] = {}
    root = node_to_jsonld(tree, tree.get_root(), base, [0], [0], ids)
    resolve_antecedents(tree, root, ids)

    # posix() rather than str(): a Windows-style `datasets\demo.cgel` would make
    # output machine-dependent.
    out: dict[str, Any] = {'@id': base, '@type': 'Tree', 'source': posix(source)}

    # Convenience accessors for the headers most consumers want. `metadata`
    # below stays authoritative -- it is what round-tripping reads.
    if 'sent_id' in tree.metadata:
        out['sentId'] = tree.metadata['sent_id']
    if 'sent_num' in tree.metadata:
        try:
            out['sentNum'] = int(tree.metadata['sent_num'])
        except ValueError:
            pass
    if 'text' in tree.metadata:
        out['text'] = tree.metadata['text']
    if 'sent' in tree.metadata:
        out['sent'] = tree.metadata['sent']

    out['metadata'] = [{'key': k, 'value': v} for k, v in tree.metadata.items()]
    out['root'] = root
    return out


def read_trees(path: str | Path) -> list[cgel.Tree]:
    """Parse every tree in one .cgel file, checking the round-trip as we go."""
    with open_read(path) as f:
        return list(cgel.trees(f, check_format=True))


def convert(paths: Sequence[Path], labels: Sequence[Path] | None = None) -> dict[str, Any]:
    """Build a JSON-LD corpus document from .cgel files.

    `labels` overrides the path recorded as each file's `source` (and used to
    mint its tree IRIs). The text pipeline uses it to attribute trees to the
    original .txt input rather than to the throwaway .cgel it parses from.
    """
    if labels is None:
        labels = paths
    trees: list[dict[str, Any]] = []
    for path, label in zip(paths, labels):
        for i, tree in enumerate(read_trees(path)):
            trees.append(tree_to_jsonld(tree, Path(label), i))
    return {'@context': CONTEXT, '@type': 'Corpus', 'trees': trees}


def dumps(doc: dict[str, Any], indent: int = 2) -> str:
    """Serialize a corpus document. `indent=0` gives one compact line."""
    # ensure_ascii=False keeps the corpus's non-ASCII text readable; the file is
    # written as UTF-8 either way.
    return json.dumps(doc, ensure_ascii=False, indent=indent if indent > 0 else None)


def write(doc: dict[str, Any], output: Path, indent: int = 2) -> None:
    write_text(output, dumps(doc, indent) + '\n')


# ---------------------------------------------------------------- json -> cgel

def jsonld_to_node(n: dict[str, Any]) -> cgel.Node:
    """Rebuild a cgel.Node so we can reuse its canonical __str__ serializer.

    Constructed with an empty `constituent` to bypass the label-parsing in
    Node.__init__ -- `category` and `index` are already separated here.
    The root has no `function`, so it gets the same empty deprel the PENMAN parser gives it.
    """
    node = cgel.Node(n.get('function') or '', '', -1)
    node.constituent = n['category']
    node.label = n.get('index')
    node.text = n.get('text')
    node._lemma = n.get('lemma')
    node.xpos = n.get('xpos')
    node.correct = n.get('correct')
    node.note = n.get('note')
    node.prepunct = list(n.get('prePunct', []))
    node.postpunct = list(n.get('postPunct', []))
    subtokens = n.get('subtokens')
    node.substrings = [(':' + s['kind'], s['value']) for s in subtokens] if subtokens else None
    return node


def jsonld_to_cgel(t: dict[str, Any]) -> str:
    """Re-serialize one JSON-LD tree as PENMAN notation, headers included."""
    def render(n: dict[str, Any], depth: int) -> str:
        s = '    ' * depth + str(jsonld_to_node(n))
        for c in n.get('children', []):
            s += '\n' + render(c, depth + 1)
        return s + ')'

    headers = ''.join(f'# {e["key"]} = {e["value"]}\n' for e in t['metadata'])
    return headers + render(t['root'], 0)


def round_trip(doc: dict[str, Any], paths: Sequence[Path]) -> int:
    """Re-serialize every tree and diff against the original .cgel text."""
    originals: list[str] = []
    for path in paths:
        for tree in read_trees(path):
            originals.append(tree.draw(include_metadata=True))

    failures = 0
    for original, t in zip(originals, doc['trees']):
        rebuilt = jsonld_to_cgel(t)
        if rebuilt != original:
            failures += 1
            log(f'round-trip MISMATCH in {t["@id"]}:')
            log(cgel.linediff(original, rebuilt))
    return failures


# ------------------------------------------------------------------ validation

def validate(doc: dict[str, Any]) -> int:
    """Check a corpus document against the packaged JSON Schema.

    Returns the number of violations; each is reported to stderr.
    """
    import jsonschema

    schema = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))
    for e in errors:
        location = '/'.join(str(p) for p in e.absolute_path)
        log(f'schema error at /{location}: {e.message}')
    return len(errors)
