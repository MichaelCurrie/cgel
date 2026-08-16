"""Raw English text -> CGEL trees, via Stanza's UD parser.

Two stages:

1. Stanza parses the text into UD CoNLL-U (EWT models -- the same treebank
   CGELBank annotates).
2. :func:`.ud2cgel.convert` runs the packaged DepEdit rules and projects the
   constituents, producing ``.cgel``.

The output is *silver* data: an automatic conversion, not a hand-checked
annotation. Some nodes will carry lowercase deprels where the UD relation had
no CGEL counterpart.

Stanza is imported lazily, inside the functions that need it, so that merely
importing this package -- or converting a ``.cgel`` file, which needs none of
this -- does not drag in torch.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from .io_utils import log, read_text, write_text
from .ud2cgel import convert as ud_to_cgel

#: Stanza processors needed to produce a dependency parse with lemmas and XPOS.
PROCESSORS = 'tokenize,mwt,pos,lemma,depparse'

#: English Web Treebank models: the treebank CGELBank itself annotates.
PACKAGE = 'ewt'


@lru_cache(maxsize=1)
def _pipeline():
    """Build (once) the Stanza pipeline. Downloads models on first use."""
    import stanza

    log('Loading Stanza pipeline (downloads EWT models on first run)...')
    return stanza.Pipeline(
        lang='en',
        processors=PROCESSORS,
        package=PACKAGE,
        tokenize_no_ssplit=True,    # treat each line as one sentence
        download_method=stanza.DownloadMethod.REUSE_RESOURCES,
    )


def text_to_conllu(text: str, out_path: str | Path) -> Path:
    """Parse `text` into UD and write CoNLL-U to `out_path`."""
    from stanza.utils.conll import CoNLL

    out_path = Path(out_path)
    log('Parsing text with Stanza...')
    doc = _pipeline()(text)
    # CoNLL.write_doc2conll opens the file itself, so hand it a str path.
    CoNLL.write_doc2conll(doc, str(out_path))
    return out_path


def text_to_cgel(text: str, workdir: str | Path, stem: str = 'input') -> Path:
    """Convert raw text to a ``.cgel`` file under `workdir`; return its path.

    `workdir` also collects the intermediate ``.conllu`` files and the DepEdit
    coverage report, which is useful when a conversion looks wrong.
    """
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    conllu_path = text_to_conllu(text, workdir / f'{stem}.ud.conllu')
    return ud_to_cgel(
        infile=conllu_path,
        resfile=workdir / f'{stem}.report.txt',
        outfile=workdir / stem,
    )


def file_to_cgel(path: str | Path, workdir: str | Path) -> Path:
    """Convert a plain-text file (one sentence per line) to a ``.cgel`` file."""
    path = Path(path)
    return text_to_cgel(read_text(path), workdir, stem=path.stem)


def write_cgel(text: str, out_path: str | Path, workdir: str | Path) -> Path:
    """Convert raw text and copy the resulting ``.cgel`` to `out_path`."""
    produced = text_to_cgel(text, workdir)
    write_text(out_path, read_text(produced))
    return Path(out_path)
