#!/usr/bin/env python3
"""Split the gold CGELBank trees into one JSON file and one text file per tree.

    python3 toy1/make_corpus.py          # run from the repository root

Reads the four gold files at the top of datasets/ and writes toy1/cgelbank_corpus/:

    <name>.json   the tree as a one-tree JSON-LD corpus, in the format of cgelbank.jsonld
    <name>.txt    the sentence text (the tree's "# text" header), one line
    index.csv     one row per tree: name, source, sent_id, sent_num, words, text

<name> is <dataset>-<number>-<first words>, e.g. twitter-017-the-preface-was-written-by-sue.
The conversion is done by packages/cgel-json-converter. Every file is checked before it is
written: it validates against the converter's JSON Schema, it converts back to exactly the
original tree text, and its tree equals the same tree in cgelbank.jsonld. Any failure stops
the script with a nonzero exit and writes nothing.
"""

from __future__ import annotations

import csv
import io
import json
import re
import shutil
import sys
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "packages" / "cgel-json-converter" / "src"))

from cgel_json_converter import convert, dumps, jsonld_to_cgel, read_trees, validate  # noqa: E402

OUT = ROOT / "toy1" / "cgelbank_corpus"
GOLD = {  # gold file -> short dataset name used in file names
    "datasets/ewt.cgel": "ewt",
    "datasets/ewt-test_iaa50.cgel": "ewt-iaa50",
    "datasets/ewt-test_pilot5.cgel": "ewt-pilot5",
    "datasets/twitter.cgel": "twitter",
}
SLUG_WORDS = 8


def slug(text: str) -> str:
    """The first words of the sentence, lowercase ASCII letters and digits, joined by hyphens."""
    words = re.findall(r"[a-z0-9]+", text.lower().encode("ascii", "ignore").decode())
    return "-".join(words[:SLUG_WORDS]) or "untitled"


def main() -> int:
    reference = {t["@id"]: t for t in json.loads((ROOT / "cgelbank.jsonld").read_text(encoding="utf-8"))["trees"]}
    files, rows, problems = {}, [], []
    for source, dataset in GOLD.items():
        doc = convert([Path(source)])
        originals = [t.draw(include_metadata=True) for t in read_trees(ROOT / source)]
        if len(originals) != len(doc["trees"]):
            problems.append(f"{source}: {len(originals)} trees read but {len(doc['trees'])} converted")
            continue
        for number, (tree, original) in enumerate(zip(doc["trees"], originals), start=1):
            name = f"{dataset}-{number:03d}-{slug(tree['text'])}"
            single = {"@context": doc["@context"], "@type": doc["@type"], "trees": [tree]}
            report = io.StringIO()
            with redirect_stderr(report):
                invalid = validate(single)
            if invalid:
                problems.append(f"{name}: {invalid} schema violations\n{report.getvalue()}")
            if jsonld_to_cgel(tree) != original:
                problems.append(f"{name}: does not convert back to the original tree text")
            if reference.get(tree["@id"]) != tree:
                problems.append(f"{name}: differs from {tree['@id']} in cgelbank.jsonld")
            if name in files:
                problems.append(f"{name}: two trees with the same name")
            files[name] = (dumps(single, indent=2), tree["text"] + "\n")
            rows.append([name, source, tree.get("sentId", ""), tree.get("sentNum", ""),
                         len(tree.get("sent", "").split()), tree["text"]])
    if len(files) != len(reference):
        problems.append(f"{len(files)} trees written but cgelbank.jsonld has {len(reference)}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name, (json_text, text) in files.items():
        (OUT / f"{name}.json").write_text(json_text if json_text.endswith("\n") else json_text + "\n",
                                          encoding="utf-8", newline="")
        (OUT / f"{name}.txt").write_text(text, encoding="utf-8", newline="")
    with open(OUT / "index.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(["name", "source", "sent_id", "sent_num", "words", "text"])
        writer.writerows(rows)
    print(f"{len(files)} trees written to {OUT.relative_to(ROOT)}: each validated, round-tripped, "
          f"and identical to cgelbank.jsonld.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
