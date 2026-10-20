"""Turn downloaded MSBA Designer Selection Panel pages into tables.

Reads the raw files in data/raw and data/reference and writes tidy CSVs
under data/processed. Does not score firms or answer the investigation
questions.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REF = ROOT / "data" / "reference"
OUT = ROOT / "data" / "processed"

MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
DATE_RE = re.compile(
    r"(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
    re.I,
)
MEETING_RE = re.compile(r"designer selection panel meeting results?\b", re.I)
MEETING_DATE_RE = re.compile(r"meeting date\s*:", re.I)
FIRM_LINE_RE = re.compile(r"^(?:(\d+)\.|[•●])\s+(.+)$")
POOL_WORD_RE = re.compile(r"boiler|window|roof|door", re.I)
NEXT_MEETING_RE = re.compile(r"^\s*the next\b", re.I)


def clean(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def parse_date(text: str) -> str:
    match = DATE_RE.search(text or "")
    if not match:
        return ""
    month, day, year = match.groups()
    return f"{int(year):04d}-{MONTHS[month.lower()]:02d}-{int(day):02d}"


class BodyBlocks(HTMLParser):
    """Extract paragraph and list blocks from the page body that holds results."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.in_body = False
        self.nested_divs = 0
        self.buf: list[tuple[str, bool]] = []
        self.in_strong = False
        self.strong_depth = 0
        self.list_stack: list[dict] = []
        self.blocks: list[dict] = []
        self._bodies: list[list[dict]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in ("script", "style"):
            self.skip += 1
            return
        if self.skip:
            return
        attr = {key: value or "" for key, value in attrs}
        classes = attr.get("class", "")
        if (
            not self.in_body
            and tag == "div"
            and "field--name-body" in classes
            and "field__item" in classes
        ):
            self.in_body = True
            self.nested_divs = 0
            self.blocks = []
            self.buf = []
            return
        if not self.in_body:
            return
        if tag == "div":
            self._flush_paragraph()
            self.nested_divs += 1
        elif tag in ("p", "h1", "h2", "h3", "h4", "hr"):
            self._flush_paragraph()
            if tag == "hr":
                self.blocks.append({"type": "hr"})
        elif tag in ("ol", "ul"):
            self._flush_paragraph()
            self.list_stack.append({"type": tag, "items": [], "buf": []})
        elif tag == "li" and self.list_stack:
            self.list_stack[-1]["buf"] = []
        elif tag in ("strong", "b"):
            self.strong_depth += 1
            self.in_strong = True
        elif tag == "br":
            self._push("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
            return
        if not self.in_body or self.skip:
            return
        if tag in ("strong", "b") and self.strong_depth:
            self.strong_depth -= 1
            self.in_strong = self.strong_depth > 0
        elif tag == "li" and self.list_stack:
            item = clean("".join(self.list_stack[-1]["buf"]))
            if item:
                self.list_stack[-1]["items"].append(item)
            self.list_stack[-1]["buf"] = []
        elif tag in ("ol", "ul") and self.list_stack:
            finished = self.list_stack.pop()
            if self.list_stack:
                self.list_stack[-1]["buf"].append(" ".join(finished["items"]))
            elif finished["items"]:
                self.blocks.append(
                    {"type": "list", "list_type": finished["type"], "items": finished["items"]}
                )
        elif tag in ("p", "h1", "h2", "h3", "h4"):
            self._flush_paragraph(tag=tag)
        elif tag == "div":
            self._flush_paragraph()
            if self.nested_divs == 0:
                self._bodies.append(self.blocks)
                self.blocks = []
                self.in_body = False
            else:
                self.nested_divs -= 1

    def handle_data(self, data: str) -> None:
        if self.skip or not self.in_body:
            return
        self._push(data)

    def _push(self, data: str) -> None:
        if self.list_stack:
            self.list_stack[-1]["buf"].append(data)
            return
        self.buf.append((data, self.in_strong))

    def _flush_paragraph(self, tag: str = "p") -> None:
        raw = "".join(piece for piece, _ in self.buf)
        strong = clean("".join(piece for piece, is_strong in self.buf if is_strong))
        lines = self._lines(self.buf)
        self.buf = []
        content_lines = [line for line in lines if line["text"]]
        firmish = sum(1 for line in content_lines if firm_marker(line["text"])[1] != line["text"])
        if len(content_lines) >= 3 or firmish >= 2:
            self.blocks.append(
                {
                    "type": "list",
                    "list_type": "lines",
                    "items": content_lines,
                    "text": clean(raw),
                    "strong": strong,
                }
            )
            return
        text = clean(raw)
        if text:
            self.blocks.append({"type": "text", "tag": tag, "text": text, "strong": strong})

    @staticmethod
    def _lines(pieces: list[tuple[str, bool]]) -> list[dict]:
        lines: list[dict] = []
        current: list[tuple[str, bool]] = []
        for piece, is_strong in pieces:
            parts = piece.split("\n")
            for index, part in enumerate(parts):
                if index:
                    lines.append(BodyBlocks._line(current))
                    current = []
                if part:
                    current.append((part, is_strong))
        lines.append(BodyBlocks._line(current))
        return lines

    @staticmethod
    def _line(pieces: list[tuple[str, bool]]) -> dict:
        text = clean("".join(piece for piece, _ in pieces))
        strong_chars = sum(len(piece.strip()) for piece, is_strong in pieces if is_strong)
        plain_chars = sum(len(piece.strip()) for piece, is_strong in pieces if not is_strong)
        return {"text": text, "header": bool(text) and strong_chars > 0 and plain_chars == 0}

    def best_body(self) -> list[dict]:
        self.close()
        if self.in_body and self.blocks:
            self._bodies.append(self.blocks)
        ranked = []
        for blocks in self._bodies:
            blob = " ".join(block.get("text", "") for block in blocks if block["type"] == "text")
            if "Designer Selection" in blob or "Meeting Date" in blob:
                ranked.append(blocks)
        if not ranked:
            return []
        return max(ranked, key=len)


def classify(intro: str) -> str:
    text = intro.lower()
    if "informational" in text:
        return "informational"
    if "disqualif" in text or "non-responsive" in text:
        return "disqualified"
    if "qualifying the following" in text:
        return "qualified_applicant"
    if "unranked" in text:
        return "unranked_applicants"
    if "awarding the following" in text:
        return "award"
    if "ranking" in text or "ranked list" in text:
        return "final_ranking"
    if "accelerated repair" in text or "recommendation of applicants" in text:
        return "pool_recommendation"
    if "interview" in text:
        return "interview_list"
    return "unclassified"


def heading_before_narrative(intro: str) -> str:
    """School name sits before the dash that introduces the applications sentence."""
    match = re.search(r"\s*[–—-]\s*a?pplications?\b", intro, re.I)
    if not match:
        match = re.search(r"\s*[–—-]\s*following\b", intro, re.I)
    if not match:
        return ""
    head = intro[: match.start()].strip(" -–—")
    if not head or len(head) > 220 or "resulted" in head.lower():
        return ""
    return head


def project_label(intro: str, strong: str, pending: str) -> str:
    head = heading_before_narrative(intro)
    if head:
        return head
    if (
        strong
        and compact(strong) != compact(intro)
        and len(strong) < 180
        and "application" not in strong.lower()
    ):
        return strong
    if pending and "resulted" not in pending.lower() and len(pending) < 140:
        return pending
    return ""


def is_date_only(text: str) -> bool:
    match = DATE_RE.search(text)
    if not match:
        return False
    remainder = DATE_RE.sub("", text)
    remainder = re.sub(
        r"meeting date|designer selection panel meeting results?|tuesday|wednesday|"
        r"thursday|friday|monday|saturday|sunday|:|,",
        "",
        remainder,
        flags=re.I,
    )
    return len(clean(remainder)) == 0 and len(text) < 160


def is_meeting_header(block: dict) -> bool:
    text = block["text"]
    if NEXT_MEETING_RE.search(text):
        return False
    if MEETING_RE.search(text) and len(text) < 220:
        return True
    if MEETING_DATE_RE.search(text) and len(text) < 140:
        return True
    return is_date_only(text)


def is_pool_category(text: str) -> bool:
    stripped = text.strip(" :")
    if not stripped or len(stripped) > 80:
        return False
    if re.search(r"school|resulted|applicant|program|review", stripped, re.I):
        return False
    return bool(POOL_WORD_RE.search(stripped))


def looks_like_project_line(text: str) -> bool:
    if len(text) < 8 or len(text) > 160:
        return False
    if re.search(r"resulted|applicant|application|interview|meeting|dsp|program|ranking", text, re.I):
        return False
    return bool(re.search(r"[–—-]", text))


def firm_marker(text: str) -> tuple[str, str]:
    match = FIRM_LINE_RE.match(text.strip())
    if not match:
        return "", text.strip()
    return match.group(1) or "", match.group(2).strip()


def is_project_title(block: dict) -> bool:
    text = block["text"]
    strong = block["strong"]
    if not strong or len(text) > 220 or is_date_only(text):
        return False
    if MEETING_RE.search(text) or NEXT_MEETING_RE.search(text):
        return False
    folded_text = compact(text)
    folded_strong = compact(strong)
    return folded_text == folded_strong or folded_text.startswith(folded_strong)


def parse_archive(path: Path, period: str) -> list[dict]:
    parser = BodyBlocks()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    rows: list[dict] = []
    meeting_raw = ""
    pending_project = ""
    pool_context = False
    pool_category = ""
    last_project = ""
    narrative: list[dict] = []

    def narrative_text() -> str:
        return clean(" ".join(block["text"] for block in narrative))

    def narrative_strong() -> str:
        strongs = [block["strong"] for block in narrative if block.get("strong")]
        return strongs[-1] if strongs else ""

    def emit(kind: str, list_type: str, position: int | str, firm: str, intro: str, label: str) -> None:
        rows.append(row_for(period, path, meeting_raw, label, kind, list_type, position, firm, intro))

    def label_for(kind: str, intro: str, strong: str) -> str:
        if kind == "informational":
            return ""
        label = project_label(intro, strong, pending_project)
        category = pool_category.strip(" :")
        if kind == "pool_recommendation" and category and category.lower() not in label.lower():
            label = f"{label} — {category}" if label else category
        return label

    for block in parser.best_body():
        if block["type"] == "hr":
            pool_context = False
            pool_category = ""
            narrative = []
            continue
        if block["type"] == "text":
            if is_meeting_header(block):
                meeting_raw = block["text"]
                pending_project = ""
                pool_context = False
                pool_category = ""
                last_project = ""
                narrative = []
                continue
            marker_position, _ = firm_marker(block["text"])
            if firm_marker(block["text"])[1] != block["text"] and len(block["text"]) < 180:
                intro = narrative_text()
                kind = classify(intro)
                if kind == "unclassified" and pool_context:
                    kind = "pool_recommendation"
                if kind == "unclassified" and marker_position:
                    kind = "final_ranking"
                _, firm = firm_marker(block["text"])
                position = int(marker_position) if marker_position else ""
                emit(kind, "line", position, firm, intro, label_for(kind, intro, narrative_strong()))
                continue
            if is_pool_category(block["text"]):
                pool_category = block["text"]
                pool_context = True
                narrative.append(block)
                continue
            if is_project_title(block) or looks_like_project_line(block["text"]):
                pending_project = block["strong"] or block["text"]
                pool_category = ""
                if "repair" not in pending_project.lower():
                    pool_context = False
            if re.search(
                r"green repair|accelerated repair|pre-qualification|recommendation of applicants",
                block["text"],
                re.I,
            ):
                pool_context = True
            if not NEXT_MEETING_RE.search(block["text"]):
                narrative.append(block)
            continue

        intro = narrative_text()
        strong = narrative_strong()
        items = block["items"]
        list_type = block["list_type"]
        if not intro and pool_context:
            kind = "pool_recommendation"
        elif not intro and rows:
            kind = "list_followup"
        elif list_type == "lines" and pool_context:
            kind = "pool_recommendation"
        else:
            kind = classify(intro)
            if kind == "unclassified" and pool_context:
                kind = "pool_recommendation"
            if kind == "unclassified" and list_type == "ol":
                kind = "final_ranking"
        label = label_for(kind, intro, strong)
        if kind == "list_followup" and not label:
            label = last_project or pending_project
        if label:
            last_project = label
        category = ""
        position = 0
        for item in items:
            text = item["text"] if isinstance(item, dict) else item
            header = item["header"] if isinstance(item, dict) else False
            if header or is_pool_category(text):
                category = text.strip(" :")
                position = 0
                continue
            marker_position, firm = firm_marker(text)
            position += 1
            item_label = label
            if category and category.lower() not in item_label.lower():
                item_label = f"{label} — {category}" if label else category
            item_position: int | str = position if list_type == "ol" or marker_position else ""
            if marker_position:
                item_position = int(marker_position)
            emit(kind, list_type, item_position, firm, intro, item_label)
        narrative = []
        pool_category = ""
    return rows


def row_for(
    period: str,
    path: Path,
    meeting_raw: str,
    label: str,
    kind: str,
    list_type: str,
    position: int | str,
    firm: str,
    intro: str,
) -> dict:
    return {
        "source_period": period,
        "source_file": path.name,
        "meeting_date_raw": meeting_raw,
        "meeting_date": parse_date(meeting_raw),
        "project": label,
        "list_kind": kind,
        "list_type": list_type,
        "position": position,
        "firm_raw": firm,
        "tied_flag": "tied" in firm.lower(),
        "intro": intro,
    }


def excel_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return ""


def parse_chart(path: Path) -> tuple[list[dict], list[dict]]:
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = workbook.active
    projects: list[dict] = []
    firms: list[dict] = []
    current: dict | None = None
    project_index = 0
    for row in sheet.iter_rows(min_row=3, values_only=True):
        marker = row[0]
        if isinstance(marker, datetime) or (isinstance(marker, str) and marker.strip()):
            project_index += 1
            status = marker.strip() if isinstance(marker, str) else ""
            current = {
                "project_id": f"chart-{project_index:03d}",
                "application_review_date": excel_date(marker),
                "interview_date": excel_date(row[1]),
                "district": (row[2] or "") if not status else "",
                "school": (row[3] or "") if not status else "",
                "est_construction_cost": (row[4] or "") if not status else "",
                "minimum_mbe_wbe_vbe": (row[5] or "") if not status else "",
                "comments": (row[10] or "") if not status else "",
                "status_note": status,
                "source_file": path.name,
            }
            projects.append(current)
            if status:
                current = None
                continue
        if current is None:
            continue
        applicant = row[6]
        shortlisted = row[8]
        if applicant:
            firms.append(
                {
                    "project_id": current["project_id"],
                    "stage": "application",
                    "firm_raw": str(applicant).strip(),
                    "rank": row[7] if row[7] is not None else "",
                }
            )
        if shortlisted:
            firms.append(
                {
                    "project_id": current["project_id"],
                    "stage": "final",
                    "firm_raw": str(shortlisted).strip(),
                    "rank": row[9] if row[9] is not None else "",
                }
            )
    return projects, firms


def parse_panel(path: Path) -> list[dict]:
    parser = BodyBlocks()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    rows: list[dict] = []
    capture = False
    for block in parser.best_body():
        if block["type"] == "text" and "MSBA Designer Selection Panel" in block["text"]:
            capture = True
            continue
        if capture and block["type"] == "list":
            for index, item in enumerate(block["items"], start=1):
                rows.append({"seat_order": index, "member_raw": item, "source_file": path.name})
            break
        if capture and block["type"] == "text" and block["text"].startswith("In addition"):
            break
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    archives = [
        ("2007-2009", RAW / "results_2007-2009.html"),
        ("2010-2014", RAW / "results_2010-2014.html"),
        ("2015-2018", RAW / "results_2015-2018.html"),
        ("2019-2024", RAW / "results_2019-2024.html"),
    ]
    archive_rows: list[dict] = []
    for period, path in archives:
        parsed = parse_archive(path, period)
        print(f"{period}: {len(parsed)} firm rows")
        archive_rows.extend(parsed)
    before = len(archive_rows)
    seen: set[tuple[str, ...]] = set()
    unique_rows: list[dict] = []
    for row in archive_rows:
        key = tuple(row.values())
        if key in seen:
            continue
        seen.add(key)
        unique_rows.append(row)
    print(f"dropped {before - len(unique_rows)} exact duplicate rows copied twice on the source pages")
    archive_rows = unique_rows
    projects, firms = parse_chart(RAW / "DSP_Meeting_Results_Chart_2025-2026.xlsx")
    panel = parse_panel(REF / "panel_members.html")
    write_csv(OUT / "archive_firm_lists.csv", archive_rows)
    write_csv(OUT / "chart_projects.csv", projects)
    write_csv(OUT / "chart_firms.csv", firms)
    write_csv(OUT / "panel_members.csv", panel)
    print(f"chart projects: {len(projects)}; chart firm rows: {len(firms)}; panel: {len(panel)}")
    kinds: dict[str, int] = {}
    for row in archive_rows:
        kinds[row["list_kind"]] = kinds.get(row["list_kind"], 0) + 1
    print("list kinds:", kinds)
    missing_dates = sum(1 for row in archive_rows if not row["meeting_date"])
    missing_projects = sum(
        1
        for row in archive_rows
        if not row["project"] and row["list_kind"] not in ("informational",)
    )
    print(f"rows missing meeting date: {missing_dates}")
    print(f"non-informational rows missing project: {missing_projects}")


if __name__ == "__main__":
    main()
