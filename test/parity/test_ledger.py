from pathlib import Path

from scripts.check_parity import validate_ledger

LEDGER = Path("docs/parity/kysely-parity.json")


def test_parity_ledger_is_valid():
    assert validate_ledger(LEDGER) == []


def test_release_gate_rejects_unverified_records():
    errors = validate_ledger(LEDGER, release=True)

    assert any("not release-ready" in error for error in errors)
