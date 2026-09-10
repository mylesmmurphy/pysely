from __future__ import annotations

import sys
import tomllib
from pathlib import Path


def main() -> int:
    version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    if tag != f"v{version}":
        print(f"Release tag {tag!r} does not match version {version!r}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
