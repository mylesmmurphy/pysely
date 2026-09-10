import subprocess
import sys
from pathlib import Path


def test_schema_plugin_validates_scope_and_infers_rows(tmp_path: Path) -> None:
    config = tmp_path / "mypy.ini"
    config.write_text("[mypy]\nplugins = pysely.mypy\nstrict = True\n")
    source = tmp_path / "query.py"
    source.write_text(Path(__file__).with_name("schema_query.txt").read_text())
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(config), str(source)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Unknown table: missing" in result.stdout
    assert "Unknown column in query scope: pet.name" in result.stdout
    assert "Incompatible value for column id" in result.stdout
    assert "Found 3 errors" in result.stdout, result.stdout


def test_schema_plugin_validates_and_infers_writes(tmp_path: Path) -> None:
    config = tmp_path / "mypy.ini"
    config.write_text("[mypy]\nplugins = pysely.mypy\nstrict = True\n")
    source = tmp_path / "query.py"
    source.write_text(Path(__file__).with_name("schema_write.txt").read_text())
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--config-file", str(config), str(source)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Unknown table: missing" in result.stdout
    assert "Unknown write column: missing" in result.stdout
    assert "Incompatible value for column first_name" in result.stdout
    assert "Unknown column in query scope: missing" in result.stdout
    assert "Incompatible value for column id" in result.stdout
    assert "Found 7 errors" in result.stdout, result.stdout
