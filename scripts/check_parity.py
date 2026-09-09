from __future__ import annotations

import argparse
import json
from pathlib import Path

STATUSES = {
    "planned",
    "implemented_unverified",
    "verified",
    "blocked",
    "not_applicable",
    "intentional_difference",
}
REQUIRED_FIELDS = {
    "id",
    "upstream_commit",
    "upstream_source",
    "upstream_tests",
    "pysely_api",
    "dialect_support",
    "runtime_status",
    "mypy_status",
    "portable_typing_status",
    "tests",
    "difference",
}


def validate_ledger(path: Path, *, release: bool = False) -> list[str]:
    records = json.loads(path.read_text())
    errors: list[str] = []
    seen: set[str] = set()

    if not isinstance(records, list):
        return ["parity ledger must contain a JSON array"]

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            errors.append(f"record {index} must be an object")
            continue

        record_id = record.get("id", f"record {index}")
        missing = REQUIRED_FIELDS - record.keys()
        if missing:
            errors.append(f"{record_id}: missing {', '.join(sorted(missing))}")
            continue
        if record_id in seen:
            errors.append(f"{record_id}: duplicate id")
        seen.add(record_id)

        if not record["dialect_support"]:
            errors.append(f"{record_id}: dialect_support must not be empty")
        for field in ("runtime_status", "mypy_status", "portable_typing_status"):
            status = record[field]
            if status not in STATUSES:
                errors.append(f"{record_id}: invalid {field} {status!r}")
            if release and status not in {
                "verified",
                "not_applicable",
                "intentional_difference",
            }:
                errors.append(f"{record_id}: {field} is not release-ready")

        if record["difference"] and not record["tests"]:
            errors.append(f"{record_id}: differences require test evidence")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", action="store_true")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("docs/parity/kysely-parity.json"),
    )
    args = parser.parse_args()

    errors = validate_ledger(args.ledger, release=args.release)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"validated {args.ledger}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
