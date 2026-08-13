from __future__ import annotations

from pathlib import Path

import insightforge


def test_pytest_imports_the_working_tree() -> None:
    package_file = Path(insightforge.__file__).resolve()
    source_root = Path(__file__).resolve().parents[2] / "src"

    assert package_file.is_relative_to(source_root.resolve())
