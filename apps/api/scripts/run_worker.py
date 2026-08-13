from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    source_directory = Path(__file__).resolve().parents[1] / "src"
    sys.path.insert(0, str(source_directory))
    runpy.run_module("insightforge.worker", run_name="__main__")


if __name__ == "__main__":
    main()
