#!/usr/bin/env python3
"""Scratch driver: raw English text -> silver CGEL tree.

Two stages, mirroring what the repo already does piecemeal:
  1. Stanza parses the text into UD CoNLL-U (cf. convertor/app.py, scripts/parse.py).
  2. ud2cgel.convert() runs DepEdit (convertor/ud-to-cgel.ini) and projects
     constituents, writing <out>.cgel and <out>.conllu.

Must be run from the repo root, since ud2cgel.py opens convertor/ud-to-cgel.ini
by relative path.

Usage:
    python temp_txt2cgel.py "Hello, world!"
    python temp_txt2cgel.py            # uses the default sentence below
"""

import sys
from pathlib import Path

import stanza
from stanza.utils.conll import CoNLL

from ud2cgel import convert

TEMP_DATA = Path('temp_data')
OUT = TEMP_DATA / 'temp_txt2cgel_out'       # .cgel / .conllu get appended
CONLLU_IN = TEMP_DATA / 'temp_txt2cgel_ud.conllu'
RESULTS = TEMP_DATA / 'temp_txt2cgel_results.txt'


def main(text: str) -> None:
    if not Path('convertor/ud-to-cgel.ini').exists():
        sys.exit('error: run this from the repo root (convertor/ud-to-cgel.ini not found)')
    TEMP_DATA.mkdir(exist_ok=True)

    print(f'Text: {text!r}\n')

    nlp = stanza.Pipeline(
        lang='en',
        processors='tokenize,mwt,pos,lemma,depparse',
        package='ewt',              # EWT models: same treebank CGELBank annotates
        tokenize_no_ssplit=True,    # treat each line as one sentence
        download_method=stanza.DownloadMethod.REUSE_RESOURCES,
    )
    CoNLL.write_doc2conll(nlp(text), str(CONLLU_IN))

    print('--- UD (CoNLL-U) ---')
    print(CONLLU_IN.read_text(encoding='utf-8'))

    convert(str(CONLLU_IN), str(RESULTS), str(OUT))

    print('\n--- CGEL ---')
    print(OUT.with_suffix('.cgel').read_text(encoding='utf-8'))

    print('--- conversion report ---')
    print(RESULTS.read_text(encoding='utf-8'))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'Hello, world!')
