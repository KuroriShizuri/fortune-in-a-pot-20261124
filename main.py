"""Fortune in a Pot entry for make.fun.

This program writes the entry the competition grades: a single UTF-8
line in ``$MAKEFUN_OUTPUT_DIR/entry.txt`` (``/output/entry.txt`` when
the variable is not set). Standard library only, deterministic, no
network, no clock.

The competition's gate: the file must contain 1 to 120 characters,
exactly one line, and more than whitespace. The entry is written with
no trailing newline, so the file holds precisely the judged line.

Usage:
    python3 main.py               write the entry file
    python3 main.py --check       validate only, write nothing
    python3 main.py --self-test   validate, then prove the written
                                  bytes round-trip exactly
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

# The fortune itself. The wording is the judged line: do not change it.
ENTRY = "By spring, your leaves will outgrow this windowsill \u2014 and so will your keeper's excuses for buying you a bigger pot."

# The entry as the exact bytes written to disk. Single source of truth
# for what the grader reads; ENTRY is its decoded form.
ENTRY_BYTES = ENTRY.encode("utf-8")

CHAR_MIN = 1
CHAR_MAX = 120
ENTRY_FILE = "entry.txt"

# Characters that would break the single-line gate, including Unicode
# line separators the plain "\n"/"\r" check would miss.
LINE_BREAKS = ("\n", "\r", "\x0b", "\x0c", "\u2028", "\u2029")


def entry_bytes() -> bytes:
    """The entry as the exact bytes written to disk."""
    return ENTRY_BYTES


def validate(text: str) -> list[str]:
    """Return every gate violation in `text` (empty means it passes)."""
    problems: list[str] = []
    size = len(text)
    if size < CHAR_MIN or size > CHAR_MAX:
        problems.append(
            f"length is {size} characters, must be {CHAR_MIN}-{CHAR_MAX}"
        )
    if not text.strip():
        problems.append("entry is blank or only whitespace")
    if any(br in text for br in LINE_BREAKS):
        problems.append("entry spans more than one line")
    if text.strip() != text:
        problems.append("entry starts or ends with whitespace")
    if "  " in text:
        problems.append("entry contains a double space")
    for char in text:
        if ord(char) < 0x20 or ord(char) == 0x7F:
            problems.append(
                f"entry contains a control character (U+{ord(char):04X})"
            )
            break
    return problems


def validate_bytes(data: bytes) -> list[str]:
    """Validate the exact bytes that will land in the entry file."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["entry bytes are not valid UTF-8"]
    if data != ENTRY_BYTES:
        return ["entry bytes differ from ENTRY_BYTES"]
    return validate(text)


def output_dir() -> Path:
    """Where the entry goes: $MAKEFUN_OUTPUT_DIR, else /output."""
    return Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))


def write_entry(directory: Path) -> Path:
    """Write the entry to `directory/entry.txt` in byte mode.

    Returns the path; raises EntryWriteError on failure, and refuses
    to leave a file whose bytes are not exactly ENTRY_BYTES.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / ENTRY_FILE
        target.write_bytes(entry_bytes())
    except OSError as exc:
        raise EntryWriteError(f"cannot write into {directory}: {exc}") from exc
    if target.read_bytes() != ENTRY_BYTES:
        raise EntryWriteError(f"bytes on disk differ in {target}")
    return target


def read_back(path: Path) -> str:
    """Read the entry file back as UTF-8 text."""
    return path.read_text(encoding="utf-8")


class EntryWriteError(Exception):
    """Raised when the entry file cannot be written."""


def self_test() -> int:
    """Validate the entry, then check a write/read round-trip."""
    problems = validate_bytes(ENTRY_BYTES)
    if problems:
        print("self-test FAIL: " + "; ".join(problems), file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory() as scratch:
        target = write_entry(Path(scratch))
        if target.read_bytes() != entry_bytes():
            print("self-test FAIL: bytes on disk differ from ENTRY_BYTES",
                  file=sys.stderr)
            return 1
        if read_back(target) != ENTRY:
            print("self-test FAIL: text on disk differs from ENTRY",
                  file=sys.stderr)
            return 1
    print(f"self-test OK: {len(ENTRY)} chars, one line, "
          "round-trip byte-identical")
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Command-line options for the entry writer."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=None,
                        help="output directory (default: "
                             "$MAKEFUN_OUTPUT_DIR or /output)")
    parser.add_argument("--check", action="store_true",
                        help="validate the entry only; write nothing")
    parser.add_argument("--self-test", action="store_true",
                        help="validate and check a byte-identical "
                             "write/read round-trip, then exit")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.check:
        problems = validate_bytes(ENTRY_BYTES)
        if problems:
            print("check FAIL: " + "; ".join(problems), file=sys.stderr)
            return 1
        print(f"check OK: entry is valid ({len(ENTRY)} chars)")
        return 0

    if args.self_test:
        return self_test()

    problems = validate_bytes(ENTRY_BYTES)
    if problems:
        print("invalid entry: " + "; ".join(problems), file=sys.stderr)
        return 1

    directory = Path(args.out) if args.out else output_dir()
    try:
        target = write_entry(directory)
    except EntryWriteError as exc:
        print(f"write FAIL: {exc}", file=sys.stderr)
        return 1
    if read_back(target) != ENTRY:
        print(f"read-back mismatch in {target}", file=sys.stderr)
        return 1
    print(f"wrote {target} ({len(ENTRY)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
