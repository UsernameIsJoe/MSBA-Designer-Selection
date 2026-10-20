"""Paths, seeds, and model defaults."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
REFERENCE = DATA / "reference"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
MANIFESTS = DATA / "manifests"
REPORTS = ROOT / "reports"
DASHBOARD = ROOT / "dashboard"

SEED = int(os.environ.get("MSBA_SEED", "20261020"))
N_BOOTSTRAP = int(os.environ.get("MSBA_BOOTSTRAP", "40"))

# Conditional logit penalty is numerical stability only, not a substantive prior.
LOGIT_PENALTY = 1e-6
# Plackett-Luce firm strengths are shrunk toward zero. This is partial pooling.
RATING_PENALTY = 2.0
# Firm-effect model. Larger values pull infrequent firms toward the common mean.
FIRM_EFFECT_PENALTY = 4.0

# Selections before this year are a poor test of "newcomer" status because the
# public archive itself starts in 2007.
NEWCOMER_EVAL_START = 2012
# Walk-forward ratings and anomaly flags start once a training window exists.
WALK_FORWARD_START = 2013

BASE_URL = "https://www.massschoolbuildings.org"
