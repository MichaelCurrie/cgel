"""Well-formedness checks on CGEL trees themselves (as opposed to the JSON).

Two independent layers, both worth running:

* :func:`validate_cgel_files` -- structural validation of ``.cgel`` sources via
  ``cgel.Tree.validate()``, plus a check that the ``# sent =`` header agrees
  with the tree's terminals. Adapted from CGELBank's ``validate_trees.py``.
* :func:`.cgel2jsonld.validate` -- JSON Schema validation of converter output.

Both are wired into the ``cgel-to-json`` CLI; this module additionally installs
a ``cgel-validate`` entry point for checking ``.cgel`` files on their own.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from . import cgel
from .io_utils import configure_stdio, log, open_read


@dataclass
class Report:
    """Outcome of validating one or more .cgel files."""

    warnings: int = 0
    metadata_errors: int = 0
    failures: int = 0

    @property
    def total(self) -> int:
        return self.warnings + self.metadata_errors + self.failures

    @property
    def ok(self) -> bool:
        return self.total == 0

    def __str__(self) -> str:
        return (f'{self.warnings + self.failures} warnings/notices and '
                f'{self.metadata_errors} metadata errors')


def validate_cgel_files(paths: Sequence[str | Path], punct: bool = False,
                        required_fields: Sequence[str] = ()) -> Report:
    """Validate every tree in `paths`. Problems are described on stderr.

    Args:
        paths: .cgel files to check.
        punct: also check that `# text =` punctuation survives into the tree.
        required_fields: metadata headers every tree must carry.
    """
    report = Report()

    for path in paths:
        log(Path(path).as_posix())
        with open_read(path) as f:
            for tree in cgel.trees(f, check_format=True,
                                   required_fields=list(required_fields)):
                # check_format=True already ensures the parsed structure
                # re-serializes to the input text.

                # also check that the sentence line matches
                s = tree.sentence(gaps=True, punct=False)
                if tree.sent != s:
                    log('metadata error: sent/terminals mismatch (no punct)',
                        tree.sent, s)
                    report.metadata_errors += 1

                if punct:   # check punctuation (slightly fuzzy match)
                    s = tree.sentence(gaps=False, punct=True, double_period=False)
                    # dollar signs may get reordered, so just check the count matches
                    assert tree.text.count('$') == s.count('$')
                    # ignore hyphens, which may be added or removed by style
                    t = tree.text.lower().replace(' ', '').replace('$', '').replace('’', "'").replace('-', '')
                    s = s.lower().replace(' ', '').replace('$', '').replace('’', "'").replace('-', '')
                    if t != s:
                        log('metadata error: text/terminals mismatch '
                            '(w/ most punct, ignoring spaces/hyphens)', tree.text, t, s)
                        report.metadata_errors += 1

                try:
                    # cgel counts warnings globally, so this is a running total.
                    report.warnings = tree.validate()
                except AssertionError as ex:
                    report.failures += 1
                    log(f'AssertionError while validating {Path(path).as_posix()}:')
                    log(ex)
                    traceback.print_tb(ex.__traceback__, limit=2)
                    log('')

    return report


def main(argv: Sequence[str] | None = None) -> int:
    configure_stdio()
    parser = argparse.ArgumentParser(
        description='Validate well-formedness of CGEL tree annotations.')
    parser.add_argument('files', type=Path, nargs='+', help='.cgel file paths')
    parser.add_argument('--punct', action=argparse.BooleanOptionalAction,
                        help='also check that `text` punctuation is present in the tree')
    args = parser.parse_args(argv)

    report = validate_cgel_files(args.files, punct=args.punct)
    log(str(report))
    return 1 if not report.ok else 0


if __name__ == '__main__':
    sys.exit(main())
