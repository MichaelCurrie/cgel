# cgel-json-converter

Convert CGEL constituency trees — or plain English text — into annotated
JSON-LD.

[![CC BY 4.0][cc-by-shield]][cc-by]

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg

## What this is

CGEL is the syntactic formalism of the *Cambridge Grammar of the English
Language*. [CGELBank](https://github.com/nert-nlp/cgel) is a human-annotated
treebank of English in that formalism, described in
[Reynolds et al. (2023)](https://people.cs.georgetown.edu/nschneid/p/cgeltrees.pdf).
Its trees are stored in a PENMAN-style `.cgel` notation:

```
# sent_id = Tree WhatARemarkableClaim-0
# text = What a remarkable claim to make!
# sent = what a remarkable claim to make --
(NP
    :Mod (AdjP
        :Head (Adj :t "what"))
    :Head (NP
        :Det (DP
            :Head (D :t "a"))
        :Head (Nom
            :Head (x / Nom
                :Mod (AdjP
                    :Head (Adj :t "remarkable"))
                :Head (N :t "claim"))
            :Comp_ind (Clause
                :Head (VP
                    :Marker (Sdr :t "to")
                    :Head (VP
                        :Head (V :t "make" :xpos "VB" :p "!")
                        :Obj (x / GAP)))))))
```

Every node has a **function** (`:Subj`, `:Head`, `:Mod`, …) and a **category**
(`Clause`, `NP`, `Nom`, `V`, …). Terminals carry `:t` text and optionally `:l`
lemma, `:xpos`, `:p` punctuation, `:correct`, `:note`, `:subt`/`:subp`
subtokens. A variable like `x /` marks a node that a `GAP` elsewhere is
coindexed with — that is how CGEL represents displacement.

This package turns all of that into JSON-LD, and back again.

**It is self-contained on purpose.** Everything it needs lives under
`src/cgel_json_converter/`, including the JSON Schema and the DepEdit rule
file, and no module imports anything outside that directory. Copy the folder
into another repository, run `uv sync`, and it works unchanged. A test enforces
this — see [Portability](#portability-is-tested-not-assumed).

## What it produces

Each level of indentation in the `.cgel` source becomes one level of nesting
under `children`, so the JSON mirrors the constituency hierarchy directly:

```
(Clause                          {"category": "Clause", "children": [
    :Subj (NP                      {"function": "Subj", "category": "NP", "children": [
        :Head (Nom                   {"function": "Head", "category": "Nom", "children": [
            :Head (N :t "dog"))))      {"function": "Head", "category": "N", "text": "dog"} ...
```

A terminal, and the gap that points back at its antecedent:

```json
{
  "@id": "urn:cgel:demo_input:Tree%20WhatARemarkableClaim-0#n15",
  "@type": "Node",
  "function": "Head",
  "category": "V",
  "text": "make",
  "position": 6,
  "xpos": "VB",
  "postPunct": ["!"]
},
{
  "@id": "urn:cgel:demo_input:Tree%20WhatARemarkableClaim-0#n16",
  "@type": "Node",
  "function": "Obj",
  "category": "GAP",
  "index": "x",
  "antecedent": { "@id": "urn:cgel:demo_input:Tree%20WhatARemarkableClaim-0#n7" }
}
```

Notable properties of the serialization:

- **Order is preserved.** `children`, `trees`, `metadata`, `prePunct`,
  `postPunct` and `subtokens` are declared `@container: @list` in the context,
  because order is syntactically meaningful — they are RDF lists, not sets.
- **Gaps are navigable.** `resolve_antecedents()` turns the shared coindexation
  variable into an explicit `antecedent` `@id` reference. (`cgel.Tree.labels`
  records antecedents only; gaps are deliberately *not* unified with them.)
- **Terminals are numbered.** `position` is 1-based over the terminals, left to
  right, skipping gaps and nonterminals.
- **Headers are kept twice.** `metadata` is the authoritative ordered list of
  `# key = value` lines and is what round-tripping reads back;
  `sentId`/`sentNum`/`text`/`sent` are convenience copies of the headers most
  consumers want.
- **IRIs are stable.** A tree's IRI is `urn:cgel:<file stem>:<sent_id>`, falling
  back to `sent_num` then to its position in the file; nodes are `<tree IRI>#nN`
  in document order.
- **The context is inlined**, so a document is self-describing without fetching
  `https://nert-nlp.github.io/cgel/ns#`.

The mapping is **lossless**: `--round-trip` re-serializes the JSON back to
PENMAN notation via `cgel.Node.__str__` and asserts it is byte-identical to the
input. All 220 gold CGELBank trees round-trip cleanly.

Output validates against `src/cgel_json_converter/data/cgel-jsonld.schema.json`
(JSON Schema draft 2020-12), which enumerates the gold CGEL function and
category inventories.

## Install

```bash
cd packages/cgel-json-converter
uv sync
```

`uv sync` installs the runtime dependencies and the `dev` group (pytest). The
text pipeline additionally downloads Stanza's EWT models (~500 MB) the first
time it runs; nothing else needs the network.

## Use

```bash
# CGEL trees -> JSON-LD on stdout
uv run cgel-to-json demo_input.cgel

# ...or to a file, checking the mapping is lossless and the trees well-formed
uv run cgel-to-json demo_input.cgel -o output.json --round-trip --validate-trees

# plain text -> Stanza UD parse -> CGEL -> JSON-LD
uv run cgel-to-json demo_input.txt --from text -o output.json

# validate .cgel sources on their own
uv run cgel-validate demo_input.cgel
```

| flag | effect |
| --- | --- |
| `-o, --output PATH` | write here instead of stdout |
| `--from {auto,cgel,text}` | how to read the inputs (default: auto, by suffix — `.cgel` is trees, anything else is text) |
| `--indent N` | JSON indent; `0` for one compact line (default: 2) |
| `--no-validate` | skip JSON Schema validation of the output |
| `--validate-trees` | also run CGEL well-formedness checks on the trees |
| `--round-trip` | convert back to `.cgel` and verify it is unchanged |
| `--work-dir DIR` | keep the text pipeline's intermediates (default: a temp dir, discarded) |

Exit status is nonzero if anything was reported. Progress and diagnostics go to
stderr, so stdout is always pure JSON.

### As a library

```python
from pathlib import Path
from cgel_json_converter import convert, dumps, round_trip, validate

doc = convert([Path('demo_input.cgel')])
assert validate(doc) == 0                            # against the packaged schema
assert round_trip(doc, [Path('demo_input.cgel')]) == 0
print(dumps(doc, indent=2))
```

Exported from the package root: `cgel` (the tree library itself), `convert`,
`dumps`, `write`, `validate` / `validate_jsonld`, `round_trip`,
`jsonld_to_cgel`, `tree_to_jsonld`, `read_trees`, `validate_cgel_files`,
`Report`, `SCHEMA_PATH`, `DEPEDIT_CONFIG_PATH`, plus `text_to_cgel`,
`file_to_cgel` and `ud_to_cgel`. The last three are served lazily via
`__getattr__`, so `import cgel_json_converter` does not load torch.

## The text pipeline

Two stages: Stanza parses English into UD CoNLL-U using the EWT models (the same
treebank CGELBank annotates), then DepEdit rewrites UD relations into CGEL
functions and `project_categories()` inserts the unary projections CGEL requires
but dependency syntax leaves implicit (`N → Nom → NP`, `V → VP → Clause`, …).

Input is read **one sentence per line**.

The resulting trees are **silver**: an automatic conversion, not a hand-checked
annotation. The DepEdit rules do not cover every UD relation, so some nodes come
out bearing a lowercase UD deprel (`parataxis`, `obl`, …) or a function outside
the gold CGEL inventory (`Adjunct`, `Appos`, `Predet`). That is expected and not
a defect — different phrasings will hit different gaps in the rule set. Schema
validation reports them, which is usually what you want: it names exactly the
constructions the conversion could not handle. Pass `--no-validate` to take the
output as-is, and `--work-dir DIR` to inspect the intermediate CoNLL-U and the
DepEdit coverage report (`N / M sentences fully parsed`).

## Layout

```
pyproject.toml                     deps + `cgel-to-json` / `cgel-validate` entry points
demo_input.cgel                    two sample trees (coordination; a gap and its antecedent)
demo_input.txt                     two sample sentences for the text pipeline
src/cgel_json_converter/
    cgel.py                        CGEL tree library (verbatim from CGELBank)
    constituent.py                 UD->CGEL projection tables (verbatim from CGELBank)
    cgel2jsonld.py                 CGEL <-> JSON-LD, and schema validation
    ud2cgel.py                     CoNLL-U -> CGEL, via DepEdit
    txt2cgel.py                    text -> CoNLL-U, via Stanza
    tree_validation.py             CGEL tree well-formedness checks
    cli.py                         `cgel-to-json`
    io_utils.py                    UTF-8 / LF / posix-path helpers
    resources.py                   locations of the packaged data files
    data/cgel-jsonld.schema.json   JSON Schema (draft 2020-12) for the output
    data/ud-to-cgel.ini            DepEdit UD->CGEL rewrite rules
tests/
```

`cgel.py` is the substantial one (~1450 lines): `Node`, `Tree`, the PENMAN
parser (`trees()`, `parse()`), the canonical serializer (`Node.__str__`,
`Tree.draw`), `Tree.validate()`, and renderers for PTB and LaTeX/forest. It is
kept byte-identical to CGELBank's copy so the two never drift; adapt around it
rather than editing it.

`tree_validation.py` is named that, and not `validate.py`, because a submodule
of that name would shadow the re-exported `cgel_json_converter.validate`
function.

## Encoding and path conventions

Enforced through `io_utils.py`, which every module uses. These are not
incidental — they are the reason output is reproducible across machines.

- **UTF-8 everywhere.** Never the platform's locale encoding (still cp1252 on
  Windows, which mangles the non-ASCII text these corpora are full of).
  `ensure_ascii=False` keeps that text literal in the JSON rather than
  `\uXXXX`-escaped.
- **LF everywhere.** Reads use universal newlines, so a CRLF checkout parses
  identically; writes use `newline=''`, so the `\n` we emit stays a bare LF.
  `configure_stdio()` applies the same to stdout/stderr, so
  `cgel-to-json x.cgel > out.json` matches `cgel-to-json x.cgel -o out.json`.
- **POSIX paths in output.** The `source` field and tree IRIs go through
  `Path.as_posix()`, so no Windows backslashes leak into a document.

Tests cover all three: CRLF input, non-ASCII round-tripping, LF output bytes,
and backslash-free `source` fields.

## Tests

```bash
uv run pytest                                     # 43 passed, 3 skipped
CGEL_TEST_STANZA=1 uv run pytest                  # 46 passed (includes the Stanza path)
```

The Stanza tests are opt-in because they download models. Everything else runs
in under a second and needs no network.

### Portability is tested, not assumed

`tests/test_self_contained.py` walks every module's AST and fails if any of
these is true:

- a module imports a top-level name that is neither stdlib nor one of the five
  declared dependencies (`jsonschema`, `pylatexenc`, `conllu`, `depedit`,
  `stanza`);
- a relative import reaches above the package root (`from .. import …`);
- a module refers to a sibling by bare name (`import cgel`) rather than
  relatively (`from . import cgel`) — that would silently resolve to a *different*
  `cgel.py` in a host repository;
- a packaged data file has gone missing or lives outside the package.

If you add a dependency, add it to both `pyproject.toml` and the `DECLARED` set
in that test.

This was also verified by hand: the folder was copied to a temp directory
outside the repository, `uv sync` run from `pyproject.toml` alone, and both
conversion paths plus all 46 tests passed there.

## Relationship to the CGELBank repository

This package is the single source of truth for the code below. The parent
repository does not keep copies; it depends on this package as a local editable
path (`tool.uv.sources` in the repo-root `pyproject.toml`), and its scripts
import from it.

| deleted from the repo root | replaced by |
| --- | --- |
| `cgel.py` | `from cgel_json_converter import cgel` |
| `constituent.py` | `from cgel_json_converter import constituent` |
| `cgel2jsonld.py` | `cgel-to-json`, or `cgel_json_converter.cgel2jsonld` |
| `ud2cgel.py` | `cgel_json_converter.ud2cgel` |
| `validate_trees.py` | `cgel-validate`, or `cgel_json_converter.tree_validation` |
| `temp_txt2cgel.py` | `cgel-to-json --from text` |
| `schema/cgel-jsonld.schema.json` | `cgel_json_converter.SCHEMA_PATH` |
| `convertor/ud-to-cgel.ini` | `cgel_json_converter.DEPEDIT_CONFIG_PATH` |

Two behaviour changes worth knowing:

- `validate_trees.py` with no arguments defaulted to the four gold corpora;
  `cgel-validate` requires explicit file arguments.
- The published schema URL `https://nert-nlp.github.io/cgel/schema/cgel-jsonld.schema.json`
  (the schema's own `$id`) no longer has a file behind it in the repo, since
  `schema/` was removed. Nothing in either codebase dereferences that URL —
  validation always reads the packaged copy — but if the schema is meant to stay
  published at that path, a CI step should copy it back out of this package.

### Divergences from upstream CGELBank

`cgel.py` and `constituent.py` are byte-for-byte copies. The rest was adapted,
and three genuine upstream bugs were fixed here in the process:

1. **The root token's deprel.** Upstream `ud2cgel.py` passes `deprel=None` for
   the root, but CGELBank commit `0cc4dfe` added `assert deprel is not None` to
   `Tree.add_token` — so every UD→CGEL conversion raised `AssertionError`, i.e.
   the whole path was broken. This package passes `''`, which is what the PENMAN
   reader gives a root, making a converted tree indistinguishable from a parsed
   one. See `ROOT_DEPREL` in `ud2cgel.py`.
2. **Sentence splitting.** `tokenize_no_ssplit=True` makes Stanza treat a
   *double* newline as the sentence boundary; a single newline is just
   whitespace. Upstream's `temp_txt2cgel.py` fed it single-newline input, so a
   whole file collapsed into one tree. `txt2cgel.as_blocks()` rejoins lines with
   a blank line.
3. **A stale category name.** `ud-to-cgel.ini` emitted `Subdr`, which appears 0
   times across the CGELBank corpora (against 122 for `Sdr`) and is rejected by
   the schema. Renamed to `Sdr` in the packaged rule file.

Other adaptations:

- `ud2cgel.py` resolves the DepEdit rules inside the package rather than by the
  relative path `convertor/ud-to-cgel.ini`, so the working directory no longer
  matters; its corpus-specific `main()`/`combine_conllus()` drivers, which
  hard-coded `datasets/*` paths, are gone; `resfile` is now optional; progress
  output moved to stderr.
- `txt2cgel.py` replaces the scratch driver `temp_txt2cgel.py`: no repo-root
  requirement, no hard-coded `temp_data/` paths, a cached pipeline, and Stanza
  imported lazily.
- `tree_validation.py` returns a `Report` dataclass instead of printing and
  exiting, so the CLI can fold its result into one exit status.
- `cgel2jsonld.py` gained `convert(paths, labels)`: `labels` overrides the path
  recorded as each tree's `source`, which is how text-derived trees stay
  attributed to the `.txt` the user named rather than to a throwaway temp file.

## Source data

The demo trees are real CGELBank annotations, taken from `datasets/twitter.cgel`
(only their `sent_num` headers were renumbered). The gold corpora themselves
stay in the parent repository:

- `datasets/twitter.cgel` — CGEL gold trees from Twitter
- `datasets/ewt.cgel` — a sample of EWT train sentences, manually annotated
- `datasets/{ewt-test_iaa50,ewt-test_pilot5}.cgel` — adjudicated trees from the
  interannotator experiment, drawn from the EWT test split
- `datasets/oneoff/*.cgel` — ad hoc trees

## Resources

__Overview of the project:__

Brett Reynolds, Aryaman Arora, and Nathan Schneider (2023). [Unified Syntactic Annotation of English in the CGEL Framework](https://people.cs.georgetown.edu/nschneid/p/cgeltrees.pdf). *Proc. of the 17th Linguistic Annotation Workshop (LAW-XVII)*, Toronto, Canada.

```bibtex
@inproceedings{cgelbank-law,
    address = {Toronto, Canada},
    title = {Unified Syntactic Annotation of {E}nglish in the {CGEL} Framework},
    author = {Reynolds, Brett and Arora, Aryaman and Schneider, Nathan},
    year = {2023},
    month = jul,
    url = {https://people.cs.georgetown.edu/nschneid/p/cgeltrees.pdf},
    booktitle = {Proc. of the 17th Linguistic Annotation Workshop (LAW-XVII)}
}
```

__Annotation manual:__

Brett Reynolds, Nathan Schneider, and Aryaman Arora (2023). [CGELBank Annotation Manual v1.0](https://arxiv.org/abs/2305.17347). *arXiv*.

__Further analysis:__

Brett Reynolds, Aryaman Arora, and Nathan Schneider (2022). [CGELBank: CGEL as a Framework for English Syntax Annotation](http://arxiv.org/abs/2210.00394). *arXiv*.

__Source data:__

Natalia Silveira, Timothy Dozat, Marie-Catherine de Marneffe, Samuel Bowman, Miriam Connor, John Bauer, Chris Manning (2014). [A Gold Standard Dependency Corpus for English](https://aclanthology.org/L14-1067/). *Proc. of LREC '14*.

Ann Bies, Justin Mott, Colin Warner, Seth Kulick (2012). [English Web Treebank](https://catalog.ldc.upenn.edu/LDC2012T13). *LDC*.

## Licence

CC BY 4.0, as CGELBank. `cgel.py` is by Aryaman Arora (@aryamanarora); the
LaTeX/forest rendering in it is by Nathan Schneider (@nschneid).
