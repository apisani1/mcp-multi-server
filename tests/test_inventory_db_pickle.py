"""Tests that the example inventory database refuses to unpickle unexpected types."""

import os
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from examples.support import inventory_db
from examples.support.inventory_db import InventoryDatabase

MARKER_ENV = "MCP_PICKLE_TEST_EXECUTED"


class _Malicious:
    """Pickles to a call that would run a command if the file were loaded unrestricted."""

    def __reduce__(self) -> Any:
        return (os.system, (f"echo pwned > {os.environ[MARKER_ENV]}",))


@pytest.fixture(autouse=True)
def _no_autosave() -> None:
    # The module-level database saves itself to ./sample_db.pkl when garbage collected
    inventory_db.db._database_file = None  # pylint: disable=protected-access


def test_round_trip_loads(tmp_path: Path) -> None:
    """A file written by initialize_db.py (module name 'inventory_db') still loads, models included."""
    path = tmp_path / "db.pkl"
    script_dir = Path(inventory_db.__file__).parent
    subprocess.run([sys.executable, "initialize_db.py", str(path)], cwd=script_dir, check=True, capture_output=True)
    loaded = InventoryDatabase(database_file=str(path))
    loaded._database_file = None  # pylint: disable=protected-access
    products = loaded._products  # pylint: disable=protected-access
    assert products
    assert all(type(p).__name__ == "Product" and type(p) is inventory_db.Product for p in products.values())


def test_malicious_pickle_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A pickle that calls os.system raises instead of executing."""
    marker = tmp_path / "executed.txt"
    monkeypatch.setenv(MARKER_ENV, str(marker))
    path = tmp_path / "evil.pkl"
    path.write_bytes(pickle.dumps({"categories": _Malicious()}))
    with pytest.raises(pickle.UnpicklingError, match="Refusing to load"):
        InventoryDatabase(database_file=str(path))
    assert not marker.exists()
