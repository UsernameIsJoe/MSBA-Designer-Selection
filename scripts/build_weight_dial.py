"""Write the history-weight dial.

Does not rewrite data/raw and does not regenerate the stored model note.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from msba_dsp.config import PROCESSED
from msba_dsp.research.weight_dial import build_outputs, stored_full_strength_loss, write_outputs

PUBLISHED_FULL_STRENGTH_LOSS = 1.077


def main() -> None:
    frame = pd.read_csv(PROCESSED / "model_frame.csv")
    check = stored_full_strength_loss(frame)
    if abs(check - PUBLISHED_FULL_STRENGTH_LOSS) > 0.02:
        raise SystemExit(
            f"full-strength seven-term loss is {check:.4f}, published note is {PUBLISHED_FULL_STRENGTH_LOSS}"
        )
    outputs = build_outputs(frame)
    write_outputs(outputs, PROCESSED)
    print("stored full-strength check", round(check, 4))
    print(outputs["scores"].to_string(index=False))
    print(outputs["weights"].to_string(index=False))
    print(outputs["curves"].to_string(index=False))


if __name__ == "__main__":
    main()
