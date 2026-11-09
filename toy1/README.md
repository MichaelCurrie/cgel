# CGELBank Corpus for the Toy Grammar

`cgelbank_corpus/` holds the 220 gold CGELBank trees as individual files, for use as gold trees by the toy grammar in [canonical-english](https://github.com/MichaelCurrie/canonical-english) (`toy1/`). The toy grammar's test suite will require each sentence it accepts to produce exactly the CGELBank tree.

| File | Contents |
| --- | --- |
| `cgelbank_corpus/<name>.json` | One tree, as a one-tree JSON-LD corpus in the format of `cgelbank.jsonld` (the same `@context`, `@type` and tree object). |
| `cgelbank_corpus/<name>.txt` | The sentence text, from the tree's `# text` header, on one line. |
| `cgelbank_corpus/index.csv` | One row per tree: `name`, `source` (gold file), `sent_id`, `sent_num`, `words` (tokens in the `# sent` header), `text`. |
| `make_corpus.py` | The script that writes `cgelbank_corpus/`. |

`<name>` is `<dataset>-<number>-<first words>`: the dataset, the tree's position in its gold file (from 001), and up to eight words of the sentence in lowercase ASCII, for example `twitter-017-the-preface-was-written-by-sue`. The tree's own identifiers (`@id`, `sentId`, `sentNum`, `source`) are inside the JSON.

| Dataset | Gold file | Trees |
| --- | --- | --- |
| `ewt` | `datasets/ewt.cgel` | 100 |
| `ewt-iaa50` | `datasets/ewt-test_iaa50.cgel` | 50 |
| `ewt-pilot5` | `datasets/ewt-test_pilot5.cgel` | 5 |
| `twitter` | `datasets/twitter.cgel` | 65 |

## Regenerating

```bash
pip install jsonschema pylatexenc   # or: cd packages/cgel-json-converter && uv sync
python3 toy1/make_corpus.py         # from the repository root
```

The conversion is done by `packages/cgel-json-converter`. Before writing anything, the script checks every tree: it validates against the converter's JSON Schema, it converts back to exactly the original `.cgel` text, and it is identical to the same tree in `cgelbank.jsonld`. If any check fails, it writes nothing and exits with status 1. The output is deterministic, so rerunning it on unchanged gold files reproduces the same files.

## License

CGELBank is licensed under [CC BY 4.0](../LICENSE-CC-BY), and so are these files. Cite Reynolds et al. (2023), as in the repository [README](../README.md).
