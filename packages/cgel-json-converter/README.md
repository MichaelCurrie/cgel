# cgel-json-converter

Convert CGEL constituency trees — or plain English text — into annotated
JSON-LD.

This is a standalone, self-contained extraction from
[CGELBank](https://github.com/nert-nlp/cgel). Everything it needs lives under
`src/cgel_json_converter/`, including the JSON Schema and the DepEdit rule file,
and no module imports anything outside that directory. Copy the folder into
another repository and it works unchanged.

## What it produces

Each level of indentation in the `.cgel` source becomes one level of nesting
under `children`, so the JSON mirrors the constituency hierarchy directly:

```
(Clause                          {"category": "Clause", "children": [
    :Subj (NP                      {"function": "Subj", "category": "NP", "children": [
        :Head (Nom                   {"function": "Head", "category": "Nom", "children": [
            :Head (N :t "dog"))))      {"function": "Head", "category": "N", "text": "dog"} ...
```

Every node carries its grammatical `function` and syntactic `category`;
terminals additionally carry `text`, a 1-based `position`, and whatever
annotation the source supplies (`lemma`, `xpos`, `correct`, `note`, `prePunct`,
`postPunct`, `subtokens`). Gaps are linked to their antecedent by `@id`, so
coindexation is navigable rather than implied by a shared variable name.

The mapping is **lossless**: `--round-trip` re-serializes the JSON back to
PENMAN notation and asserts it is byte-identical to the input.

## Install

```bash
cd packages/cgel-json-converter
uv sync
```

`uv sync` installs the runtime dependencies and the `dev` group (pytest). The
text pipeline additionally downloads Stanza's EWT models the first time it runs.

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

Options:

| flag | effect |
| --- | --- |
| `-o, --output PATH` | write here instead of stdout |
| `--from {auto,cgel,text}` | how to read the inputs (default: by suffix) |
| `--indent N` | JSON indent; `0` for one compact line (default: 2) |
| `--no-validate` | skip JSON Schema validation of the output |
| `--validate-trees` | also run CGEL well-formedness checks |
| `--round-trip` | convert back to `.cgel` and verify it is unchanged |
| `--work-dir DIR` | keep the text pipeline's intermediates |

Exit status is nonzero if anything was reported.

### A note on the text pipeline

Input is read one sentence per line, and the resulting trees are **silver**: an
automatic UD→CGEL conversion, not a hand-checked annotation. The DepEdit rules
do not cover every UD relation, so some nodes can come out bearing a lowercase
UD deprel (`parataxis`, `obl`, …) or a function outside the CGEL inventory
(`Adjunct`, `Appos`, `Predet`). Schema validation reports those, which is
usually what you want — it names exactly the constructions the conversion could
not handle. Pass `--no-validate` to take the output as-is, and `--work-dir DIR`
to inspect the intermediate CoNLL-U and the DepEdit coverage report.

### As a library

```python
from pathlib import Path
from cgel_json_converter import convert, dumps, round_trip, validate

doc = convert([Path('demo_input.cgel')])
assert validate(doc) == 0        # against the packaged JSON Schema
assert round_trip(doc, [Path('demo_input.cgel')]) == 0
print(dumps(doc, indent=2))
```

`text_to_cgel`, `file_to_cgel` and `ud_to_cgel` are exported too, and are
imported lazily so that `import cgel_json_converter` does not load torch.

## Tests

```bash
uv run pytest                                     # everything except the Stanza path
CGEL_TEST_STANZA=1 uv run pytest                  # including it (downloads models)
```

`tests/test_self_contained.py` is the guard on portability: it walks every
module's AST and fails if anything imports outside the package or reaches above
the package root.

## Layout

```
pyproject.toml                     deps + `cgel-to-json` / `cgel-validate` entry points
demo_input.cgel                    two sample trees (coordination; a gap and its antecedent)
demo_input.txt                     two sample sentences for the text pipeline
src/cgel_json_converter/
    cgel.py                        CGEL tree library (verbatim from CGELBank)
    constituent.py                 UD->CGEL projection tables (verbatim)
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

## Encoding and path conventions

Enforced through `io_utils.py`, which every module uses:

- **UTF-8 everywhere.** Never the platform's locale encoding. `ensure_ascii=False`
  keeps non-ASCII text literal in the JSON.
- **LF everywhere.** Reads normalise CRLF to LF, so a Windows checkout parses
  identically; writes disable newline translation, so output is byte-identical
  across platforms. This also applies to redirected stdout.
- **POSIX paths in output.** The `source` field and tree IRIs go through
  `Path.as_posix()`, so no Windows backslashes leak into the document.

## Divergences from upstream CGELBank

`cgel.py` and `constituent.py` are byte-for-byte copies. The rest was adapted:

- `ud2cgel.py` resolves `ud-to-cgel.ini` inside the package rather than by the
  relative path `convertor/ud-to-cgel.ini`, so the working directory no longer
  matters; its corpus-specific `main()`/`combine_conllus()` drivers are gone;
  progress output moved to stderr so stdout stays reserved for JSON.
- `ud2cgel.py` gives the root token the empty deprel `''` instead of `None`.
  Upstream passes `None`, which trips the `assert deprel is not None` that
  `Tree.add_token` gained in CGELBank commit `0cc4dfe` — the UD→CGEL path is
  currently broken upstream. `''` is what the PENMAN reader gives a root, so a
  converted tree is indistinguishable from a parsed one.
- `txt2cgel.py` replaces the scratch driver `temp_txt2cgel.py`: no repo-root
  requirement, no hard-coded `temp_data/` paths, and Stanza is imported lazily.
  It also joins input lines with a blank line before handing them to Stanza:
  `tokenize_no_ssplit` treats a *double* newline as the sentence boundary, so
  upstream's single-newline input collapsed a whole file into one tree.
- `data/ud-to-cgel.ini` emits the category `Sdr` where upstream's copy emits
  `Subdr`. `Subdr` is a stale name — it appears 0 times in the CGELBank corpora
  and is rejected by the JSON Schema, whereas `Sdr` appears 122 times.
- `validate_trees.py` became `tree_validation.py`, returning a `Report` instead
  of printing and exiting, so the CLI can fold its result into one exit status.
  (Not `validate.py`: a submodule of that name would shadow the re-exported
  `cgel_json_converter.validate` function.)

## Licence

CC BY 4.0, as CGELBank.
