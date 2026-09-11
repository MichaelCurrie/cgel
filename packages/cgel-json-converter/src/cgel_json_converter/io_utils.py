"""Encoding- and newline-safe file I/O, shared by every module in the package.

Two invariants hold everywhere:

* **UTF-8 always.** Never the platform's locale encoding, which on Windows is
  still cp1252 and mangles the non-ASCII text that CGEL corpora are full of.
* **LF always.** Reads normalise CRLF/CR to LF (universal newlines) so a
  Windows-checkout ``.cgel`` file parses identically; writes disable newline
  translation (``newline=''``) so the ``\\n`` we emit stays a bare LF instead of
  being expanded to CRLF. Converter output is therefore byte-identical across
  platforms, which is what makes ``--round-trip`` meaningful.
"""

from __future__ import annotations

import glob as globlib
import io
import sys
from pathlib import Path
from typing import Sequence, TextIO

ENCODING = 'utf-8'


def expand_paths(patterns: Sequence[str | Path]) -> list[Path]:
    """Expand shell globs in *patterns*.

    bash/zsh expand ``datasets/*.cgel`` before the process starts. PowerShell
    and cmd.exe pass the asterisk through, so without this the CLI looks for a
    file whose name is literally ``*.cgel``.
    """
    out: list[Path] = []
    for raw in patterns:
        pattern = Path(raw).as_posix()
        if any(ch in pattern for ch in '*?['):
            matches = sorted(Path(p) for p in globlib.glob(pattern))
            if not matches:
                raise SystemExit(f'error: no such file: {pattern}')
            out.extend(matches)
        else:
            out.append(Path(raw))
    return out


def open_read(path: str | Path) -> TextIO:
    """Open for reading as UTF-8, translating any line ending to ``\\n``."""
    # newline=None selects universal-newline mode on purpose: CRLF input must
    # reach the PENMAN parser as LF or indentation checks fail on Windows.
    return Path(path).open('r', encoding=ENCODING, newline=None)


def open_write(path: str | Path) -> TextIO:
    """Open for writing as UTF-8 with untranslated (LF) line endings."""
    return Path(path).open('w', encoding=ENCODING, newline='')


def read_text(path: str | Path) -> str:
    with open_read(path) as f:
        return f.read()


def write_text(path: str | Path, text: str) -> None:
    with open_write(path) as f:
        f.write(text)


def posix(path: str | Path) -> str:
    """Render a path with forward slashes, for embedding in output documents.

    JSON-LD IRIs and the ``source`` field must not carry Windows backslashes:
    they would differ from the POSIX rendering and break byte-comparison of
    output generated on different machines.
    """
    return Path(path).as_posix()


def configure_stdio() -> None:
    """Force UTF-8 and LF on stdout/stderr, whatever the console code page says.

    ``newline='\\n'`` matters when stdout is redirected: without it the Windows
    text layer would rewrite every ``\\n`` as CRLF and `cgel-to-json x.cgel >
    out.json` would not match `cgel-to-json x.cgel -o out.json`.
    """
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding=ENCODING, newline='\n')


def log(*args: object) -> None:
    """Progress output. Always stderr, so stdout stays pure JSON."""
    print(*args, file=sys.stderr)
