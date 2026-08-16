#!/usr/bin/env python3
"""``cgel-to-json`` -- command line front end.

Accepts either CGEL trees (``.cgel``, PENMAN notation) or plain English text,
and emits one annotated JSON-LD corpus document covering all of the inputs.

    cgel-to-json demo_input.cgel                     # JSON-LD to stdout
    cgel-to-json demo_input.cgel -o out.json         # ...or to a file
    cgel-to-json demo_input.txt --from text          # parse raw text first
    cgel-to-json demo_input.cgel --round-trip        # prove the mapping is lossless

Validation against the packaged JSON Schema runs by default; `--no-validate`
turns it off. A nonzero exit status means at least one problem was reported.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from . import cgel2jsonld
from .io_utils import configure_stdio, log
from .tree_validation import validate_cgel_files

#: Suffixes read as CGEL trees under `--from auto`. Everything else is text.
CGEL_SUFFIXES = {'.cgel'}


def is_cgel(path: Path, mode: str) -> bool:
    if mode == 'cgel':
        return True
    if mode == 'text':
        return False
    return path.suffix.lower() in CGEL_SUFFIXES


def prepare_inputs(files: Sequence[Path], mode: str, workdir: Path
                   ) -> tuple[list[Path], list[Path]]:
    """Reduce every input to a .cgel file.

    Returns `(cgel_paths, labels)`: the files to parse, and the paths to record
    as each tree's `source`. They differ for text inputs, where the tree comes
    from a generated .cgel but should still be attributed to the .txt the user
    named.
    """
    cgel_paths: list[Path] = []
    labels: list[Path] = []

    for path in files:
        if not path.exists():
            raise SystemExit(f'error: no such file: {path.as_posix()}')
        if is_cgel(path, mode):
            cgel_paths.append(path)
            labels.append(path)
        else:
            # Imported here so the .cgel-only path never loads torch.
            from .txt2cgel import file_to_cgel

            log(f'{path.as_posix()}: parsing text -> CGEL')
            cgel_paths.append(file_to_cgel(path, workdir))
            labels.append(path)

    return cgel_paths, labels


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='cgel-to-json',
        description='Convert CGEL trees, or plain English text, to annotated JSON-LD.')
    parser.add_argument('files', type=Path, nargs='+',
                        help='.cgel tree files and/or plain-text files')
    parser.add_argument('-o', '--output', type=Path,
                        help='write here instead of stdout')
    parser.add_argument('--from', dest='source_format',
                        choices=('auto', 'cgel', 'text'), default='auto',
                        help='how to read the inputs (default: auto, by suffix)')
    parser.add_argument('--indent', type=int, default=2,
                        help='JSON indent; 0 for one compact line (default: 2)')
    parser.add_argument('--no-validate', action='store_true',
                        help='skip JSON Schema validation of the output')
    parser.add_argument('--validate-trees', action='store_true',
                        help='also run CGEL well-formedness checks on the trees')
    parser.add_argument('--round-trip', action='store_true',
                        help='also convert back to .cgel and verify it is unchanged')
    parser.add_argument('--work-dir', type=Path,
                        help='keep text-pipeline intermediates here '
                             '(default: a temporary directory, discarded on exit)')
    return parser


def run(args: argparse.Namespace, workdir: Path) -> int:
    """Do the conversion. Returns the number of problems found."""
    cgel_paths, labels = prepare_inputs(args.files, args.source_format, workdir)

    problems = 0
    if args.validate_trees:
        report = validate_cgel_files(cgel_paths)
        log(str(report))
        problems += report.total

    doc = cgel2jsonld.convert(cgel_paths, labels)

    if not args.no_validate:
        problems += cgel2jsonld.validate(doc)
    if args.round_trip:
        problems += cgel2jsonld.round_trip(doc, cgel_paths)

    n = len(doc['trees'])
    if args.output:
        cgel2jsonld.write(doc, args.output, args.indent)
        log(f'{n} tree(s) -> {args.output.as_posix()}')
    else:
        sys.stdout.write(cgel2jsonld.dumps(doc, args.indent) + '\n')

    return problems


def main(argv: Sequence[str] | None = None) -> int:
    configure_stdio()
    args = build_parser().parse_args(argv)

    if args.work_dir:
        args.work_dir.mkdir(parents=True, exist_ok=True)
        problems = run(args, args.work_dir)
    else:
        with tempfile.TemporaryDirectory(prefix='cgel-json-') as tmp:
            problems = run(args, Path(tmp))

    if problems:
        log(f'{problems} problem(s) found.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
