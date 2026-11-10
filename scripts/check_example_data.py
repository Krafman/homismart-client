"""Fail if a tracked file contains a HomiSmart device ID that isn't an obvious fake.

This project is developed against a real HomiSmart installation, and its data
must never be published (see AGENTS.md). HomiSmart IDs are 14 hex characters:
hubs look like MAC addresses, devices are a two-digit type plus a serial.
Examples and tests must use IDs of the form TT00000000NNNN, e.g. 01000000000001.

Names can't be checked automatically; review those yourself.
"""
from __future__ import annotations

import re
import subprocess
import sys

CANDIDATE = re.compile(r"(?<![0-9A-Za-z])[0-9A-Fa-f]{14}(?![0-9A-Za-z])")
FAKE = re.compile(r"[0-9]{2}0{8}[0-9]{4}")


def main() -> int:
    files = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    problems = []
    for path in files:
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue  # binary files (images) can't hold copied text
        for number, line in enumerate(text.splitlines(), 1):
            for match in CANDIDATE.finditer(line):
                if not FAKE.fullmatch(match.group()):
                    problems.append(f"{path}:{number}: {match.group()}")
    if problems:
        print("Device IDs that don't look like fakes (use e.g. 01000000000001):")
        print("\n".join(problems))
        return 1
    print(f"OK: no real-looking device IDs in {len(files)} tracked files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
