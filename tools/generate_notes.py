#!/usr/bin/env python3
"""Thin wrapper so `python tools/generate_notes.py ...` keeps working.

The generator lives in omop_lite/synthetic_notes.py so it ships with the
package and can run at load time (SYNTHETIC_NOTES=true).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from omop_lite.synthetic_notes import main  # noqa: E402

if __name__ == "__main__":
    main()
