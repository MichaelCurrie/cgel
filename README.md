# cgel

This repo contains CGELBank, a human-annotated treebank of English using the syntactic formalism of the *Cambridge Grammar of the English Language* (CGEL). The treebank is described in [Reynolds et al. (2023)](https://people.cs.georgetown.edu/nschneid/p/cgeltrees.pdf), published at the Linguistic Annotation Workshop (LAW).

## Quickstart

From the repo root (requires [uv](https://docs.astral.sh/uv/)):

```sh
uv sync
uv run cgel-to-json packages/cgel-json-converter/demo_input.cgel
```

That prints JSON-LD for two sample trees (`The #futureoflinguistics is integrative…` and `What a remarkable claim to make!`). Write it to a file and check the mapping is lossless with:

```sh
uv run cgel-to-json packages/cgel-json-converter/demo_input.cgel -o demo.jsonld --round-trip
```

To walk the gold trees in Python:

```python
from cgel_json_converter import cgel

with open('datasets/twitter.cgel', encoding='utf-8') as f:
    for tree in cgel.trees(f, check_format=True):
        print(tree.sentence())
```

![Status](https://github.com/nert-nlp/cgel/actions/workflows/validate.yml/badge.svg) [![CC BY 4.0][cc-by-shield]][cc-by]

This work is licensed under a
[Creative Commons Attribution 4.0 International License][cc-by].

[![CC BY 4.0][cc-by-image]][cc-by]

[cc-by]: http://creativecommons.org/licenses/by/4.0/
[cc-by-image]: https://i.creativecommons.org/l/by/4.0/88x31.png
[cc-by-shield]: https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg

## Datasets
We annotated data from Twitter and the English Web Treebank (EWT).

<table>
<tr>
<td><img src="figures/stats.png" style="height: 300px;"></td>
<td><img src="figures/tree.png" style="height: 300px;"></td>
</tr>
</table>

To load the CGEL trees for scripting, use the `cgel` module from the
[`cgel-json-converter`](packages/cgel-json-converter/) package:

```python
from cgel_json_converter import cgel

with open('datasets/twitter.cgel', encoding='utf-8') as f:
    for tree in cgel.trees(f, check_format=True):
        print(tree.sentence())
```

Summary information is available in:
- [STATS.md](STATS.md) (statistics extracted from the trees)
- [INDEX.md](INDEX.md) (list of sentences and notable properties)

### Gold Data

- `datasets/twitter.cgel`: CGEL gold trees from Twitter
- `datasets/ewt.cgel`: CGEL trees from a sample of EWT train sentences (manually annotated by Brett Reynolds)
- `datasets/{ewt-test_iaa50.cgel, ewt-test_pilot5.cgel}`: Adjudicated and up-to-date trees from the [IAA experiment](#interannotator-data); sentences drawn from the EWT test split
- `datasets/trial/{ewt-trial.cgel, twitter-etc-trial.cgel}`: Miscellaneous trees annotated but not adjudicated by both annotators
- `datasets/oneoff/*.cgel`: Various CGEL trees for ad hoc sentences

Corresponding `.conllu` files are also available alongside the `datasets/*.cgel` and `datasets/trial/*.cgel` files.
EWT `.conllu` files are gold trees; other `.conllu` files are manual corrections of Stanza output.

All data was revised with the aid of consistency-checking scripts.

Other subdirectories contain older/silver versions of the trees.

### Interannotator Data

Under `datasets/iaa/`:

- `ewt-test_pilot5.{nschneid, brettrey, adjudicated}.cgel`: Pilot interannotator study (5 sentences from EWT).
- `ewt-test_iaa50.{...}.cgel`: Main interannotator study (50 sentences from EWT).
  - `{nschneid, brettrey}.novalidator`: Initial annotation.
  - `{nschneid, brettrey}.validator`: Corrected individual annotation after running automatic validation script to catch common errors.
  - `adjudicated`: Final adjudicated version combining both annotations.

## Structure

The tree library, the converters and the validator live in a standalone package
under [`packages/cgel-json-converter/`](packages/cgel-json-converter/), so they
can be reused from other repositories without copying files around. See that
package's [README](packages/cgel-json-converter/README.md) for its full API,
CLI and internals.

| was | now |
| --- | --- |
| `cgel.py` | `from cgel_json_converter import cgel` |
| `constituent.py` | `from cgel_json_converter import constituent` |
| `cgel2jsonld.py` | `cgel-to-json` (or `cgel_json_converter.cgel2jsonld`) |
| `ud2cgel.py` | `cgel_json_converter.ud2cgel` |
| `validate_trees.py` | `cgel-validate` (or `cgel_json_converter.tree_validation`) |
| `temp_txt2cgel.py` | `cgel-to-json --from text` |
| `schema/cgel-jsonld.schema.json` | `cgel_json_converter.SCHEMA_PATH` |
| `convertor/ud-to-cgel.ini` | `cgel_json_converter.DEPEDIT_CONFIG_PATH` |

Remaining top-level scripts:

- `cgel2ptb.py`: prints CGEL trees in PTB bracketed style
- `eval.py`: script for comparing two sets of CGEL annotations with tree edit distance (and derived metrics)
- `iaa.sh`: script that runs `eval.py` on all files involved in our interannotator study (comparing pre- and post-validation trees as well as final adjudicated version)
- `tree2tex.py`: print CGEL trees in pretty LaTeX

**Folders**
- `analysis/`: scripts for analysing the datasets, incl. edit distance
- `convertor/`: outputs from UD→CGEL conversion, with a simple Flask web interface for local testing in the browser (English text > automatic UD w/ Stanza > CGEL). The DepEdit conversion rules themselves now live in `packages/cgel-json-converter/`.
- `datasets/`: all the final datasets
- `figures/`: figures for papers/posters and code for generating them
- `packages/cgel-json-converter/`: the CGEL tree library, the JSON-LD converter, the UD→CGEL converter, the tree validator, and the JSON Schema
- `scripts/`: one-off scripts that were used to clean/restructure data
- `test/`: validation tests

## Setup

```sh
$ uv sync
```

`uv sync` installs `packages/cgel-json-converter` in editable mode, so edits to
the library take effect immediately and there is exactly one copy of each
module. Commands then run as `uv run …` (for example `uv run cgel-to-json`).

## Tests

To run tests locally:

```sh
$ uv run pytest
```

This will validate the trees, test distance metrics (Levenshtein and TED), and
run the converter package's own suite.

To check tree well-formedness or produce JSON-LD directly:

```sh
$ uv run cgel-validate datasets/ewt.cgel datasets/twitter.cgel
$ uv run cgel-to-json datasets/*.cgel -o cgelbank.jsonld --round-trip
```

## History

- CGELBank 1.0: 2023-07-04.
  - Initial release of 257 trees.

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

Aryaman Arora, Nathan Schneider, and Brett Reynolds (2022). [A CGEL-formalism English treebank](https://docs.google.com/presentation/d/1muLMZyNLspXElkWaOLfGQve64SxbapXkXJpWpgNmFWw/edit). *MASC-SLL* (poster), Philadelphia, USA.

__Source data:__

Natalia Silveira, Timothy Dozat, Marie-Catherine de Marneffe, Samuel Bowman, Miriam Connor, John Bauer, Chris Manning (2014). [A Gold Standard Dependency Corpus for English](https://aclanthology.org/L14-1067/). *Proc. of the Ninth International Conference on Language Resources and Evaluation (LREC '14)*.

Ann Bies, Justin Mott, Colin Warner, Seth Kulick (2012). [English Web Treebank](https://catalog.ldc.upenn.edu/LDC2012T13). *LDC*.
