"""Firm-name resolution.

Automatic matching removes only capitalization, accents, punctuation, and legal
suffixes. Additional matches are an explicit reviewed list. Joint ventures and
associations keep their own identifiers and are not credited to a parent firm.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

LEGAL = {
    "inc",
    "llc",
    "pc",
    "ltd",
    "limited",
    "incorporated",
    "corp",
    "corporation",
    "company",
    "co",
    "llp",
    "pllc",
}
STOPWORDS = {"the", "of", "dba"}

# Exact matches on the normalized key. Each value is the canonical key.
# Reasons are documented in ALIAS_REASONS.
REVIEWED_ALIASES: dict[str, str] = {
    "smma": "symmes maini and mckee associates",
    "omr architects": "office michael rosenfeld",
    "dore and whittier architects": "dore and whittier",
    "dore and whittier associates": "dore and whittier",
    "tappe architects": "tappe",
    "tappe associates": "tappe",
    "jcj architecture": "jcj",
    "jcj architecture and interiors": "jcj",
    "jcj architects": "jcj",
    "dinisco design partnership": "dinisco design",
    "finegold alexander architects": "finegold alexander",
    "finegold alexander and associates": "finegold alexander",
    "lamoureux pagano associates": "lamoureux pagano",
    "lamoureux pagano and associates": "lamoureux pagano",
    "lamoureux pagano associates architects": "lamoureux pagano",
    "mount vernon group architects": "mount vernon group",
    "perkins and will architects": "perkins and will",
    "perkins and will architecture": "perkins and will",
    "lavallee brensigner": "lavallee brensinger",
    "lavallee brensigner architects": "lavallee brensinger architects",
    "slam collaborative": "slam",
    "jonathan levi architects": "jonathan levi",
    "jonathan levi associates": "jonathan levi",
    "flansburgh architects": "flansburgh associates",
    "flansburgh architect": "flansburgh associates",
    "miller dyer spears architects": "miller dyer spears",
    "studio g architects": "studio g",
    "raymond design associates": "raymond design",
    "design partnership cambridge": "design partnership of cambridge",
}

ALIAS_REASONS: dict[str, str] = {
    "smma": "The MSBA list prints SMMA in parentheses after Symmes Maini & McKee Associates.",
    "omr architects": "OMR is the initialism used for Office of Michael Rosenfeld in these lists. Confidence is medium because a merger document is not in the DSP file.",
    "dinisco design partnership": "Earlier lists say DiNisco Design Partnership and later lists say DiNisco Design. Treated as one continuing practice. Confidence is medium.",
    "jonathan levi architects": "Architects and Associates spellings of Jonathan Levi are treated as one practice. Confidence is medium.",
    "tappe architects": "Tappe Associates and Tappe Architects are successive published names of the same practice in these lists.",
    "jcj architecture": "JCJ Architecture, JCJ Architects, and JCJ Architecture and Interiors are successive published names.",
    "lavallee brensigner": "One-letter spelling difference, Brensigner versus Brensinger.",
}

MEDIUM_CANONICAL = {
    "office michael rosenfeld",
    "dinisco design",
    "jonathan levi",
}

JV_RE = re.compile(
    r"in association with|joint venture|\bw/\b|\bwith smma\b",
    re.IGNORECASE,
)
SLAM_RE = re.compile(r"s\s*/\s*l\s*/\s*a\s*/\s*m", re.IGNORECASE)


@dataclass(frozen=True)
class ResolvedFirm:
    firm_id: str
    canonical_key: str
    joint_venture: bool
    declined: bool
    tie_record: bool
    method: str
    confidence: str


def _firm_id(key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]
    return f"f_{digest}"


def clean_display(raw: str) -> str:
    text = raw.replace("\xa0", " ")
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"^tie:\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("|", " ")
    text = re.sub(r"\s+", " ", text).strip(" ,;-")
    return text


def is_joint_venture(raw: str) -> bool:
    if JV_RE.search(raw):
        return True
    if SLAM_RE.search(raw):
        return False
    if "/" not in raw:
        return False
    sides = [clean_display(part) for part in raw.split("/") if clean_display(part)]
    return len(sides) >= 2 and all(" " in side for side in sides)


def is_tie_record(raw: str) -> bool:
    return bool(re.match(r"\s*tie\s*:", raw, flags=re.IGNORECASE))


def declined_interview(raw: str) -> bool:
    return "declined to interview" in raw.lower()


def normalize_key(raw: str) -> str:
    text = unicodedata.normalize("NFKD", raw)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"^tie:\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("&", " and ").replace("+", " and ").replace("|", " ")
    text = SLAM_RE.sub(" slam ", text)
    text = text.replace("/", " ")
    text = text.lower().replace("turowski 2", "turowski2")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    tokens = [token for token in text.split() if token not in STOPWORDS and token not in LEGAL]
    return " ".join(tokens)


def resolve_firm(raw: str) -> ResolvedFirm:
    joint = is_joint_venture(raw)
    declined = declined_interview(raw)
    tie = is_tie_record(raw)
    key = normalize_key(raw)
    method = "normalized"
    if not joint and not tie and key in REVIEWED_ALIASES:
        key = REVIEWED_ALIASES[key]
        method = "reviewed_alias"
    confidence = "medium" if key in MEDIUM_CANONICAL and method == "reviewed_alias" else "high"
    if joint:
        method = "joint_venture_kept_separate"
        confidence = "high"
    if tie:
        method = "excluded_tie_notation"
        confidence = "low"
    if not key:
        method = "unresolved"
        confidence = "low"
    return ResolvedFirm(
        firm_id=_firm_id(key or "unresolved"),
        canonical_key=key,
        joint_venture=joint,
        declined=declined,
        tie_record=tie,
        method=method,
        confidence=confidence,
    )
