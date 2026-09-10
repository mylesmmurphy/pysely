from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


def digest(paths: list[Path]) -> str:
    value = hashlib.sha256()
    for path in sorted(paths):
        value.update(path.relative_to(SITE).as_posix().encode())
        value.update(path.read_bytes())
    return value.hexdigest()[:12]


def fingerprint(
    relative_path: str, dependencies: list[Path] | None = None
) -> tuple[str, str]:
    source = SITE / relative_path
    revision = digest([source, *(dependencies or [])])
    target = source.with_name(f"{source.stem}.{revision}{source.suffix}")
    source.rename(target)
    return source.relative_to(SITE).as_posix(), target.relative_to(SITE).as_posix()


def main() -> None:
    playground_dependencies = [
        SITE / "assets/playground-worker.js",
        SITE / "assets/playground.py",
        *list((SITE / "assets/examples").rglob("*")),
        *list((SITE / "assets/intelligence").rglob("*")),
        *list((SITE / "wheels").rglob("*")),
    ]
    playground_dependencies = [
        path for path in playground_dependencies if path.is_file()
    ]
    replacements = dict(
        [
            fingerprint("assets/site.css"),
            fingerprint("assets/playground.css"),
            fingerprint("assets/site.js"),
            fingerprint("assets/playground.js", playground_dependencies),
        ]
    )

    for page in SITE.rglob("*.html"):
        content = page.read_text()
        for source, target in replacements.items():
            content = content.replace(source, target)
        page.write_text(content)


if __name__ == "__main__":
    main()
