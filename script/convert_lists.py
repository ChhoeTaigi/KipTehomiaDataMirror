"""Parse the 5 MOE place-name list ODTs and merge them into bunji/KipTehomiaData.{csv,json}.

Reads the source `*_list.zip` archives directly from the tangloo directory
(each contains an ODT, DOCX, and PDF — we parse the ODT). Audio filenames
are looked up per source from the audio zips also in tangloo, so disambiguation
between sources that share numeric IDs (e.g. railways and tkmrt both have
號次=1) is resolved by the upstream zip the entry came from.

Pure stdlib: zipfile, xml.etree, csv, json, re.
"""

import csv
import json
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

NS_TABLE = "urn:oasis:names:tc:opendocument:xmlns:table:1.0"
NS_TEXT = "urn:oasis:names:tc:opendocument:xmlns:text:1.0"

# Audio zips per source. The `placename` document covers 5 audio categories
# (administrative/settlement/naturalentity/publicutilities/street) which use
# letter-prefixed IDs (A001, B0001, …) — those don't collide, so we union
# all 5 into a single placename audio map.
AUDIO_ZIPS = {
    "railways": ["railways_m_mp3.zip"],
    "tkmrt": ["tkmrt_m_mp3.zip"],
    "thsrc": ["thsrc_m_mp3.zip"],
    "twtrip": ["twtrip_m_mp3.zip"],
    "placename": [
        "administrative_m_mp3.zip",
        "settlement_m_mp3.zip",
        "naturalentity_m_mp3.zip",
        "publicutilities_m_mp3.zip",
        "street_m_mp3.zip",
    ],
}

CSV_COLUMNS = [
    "來源", "序號", "業者代碼", "國語",
    "臺灣台語_羅馬字", "臺灣台語_第二羅馬字", "臺灣台語_漢字建議", "臺灣台語_說明",
    "臺灣客語_羅馬字", "臺灣客語_漢字建議", "臺灣客語_說明",
    "音檔",
]

# Human-readable 來源 labels. The 4 transport docs map 1:1; the placename doc
# splits into 5 sub-categories by the leading letter of 序號 (A/B/C/D/E).
# Internal keys (railways/tkmrt/…/placename) are used during audio lookup,
# then swapped for these labels just before writing.
SOURCE_LABELS = {
    "railways": "臺灣鐵路站名",
    "tkmrt": "捷運站名",
    "thsrc": "臺灣高鐵及高鐵快捷公車站名",
    "twtrip": "台灣好行旅遊公車站名",
}

PLACENAME_PREFIX_LABELS = {
    "A": "行政區",
    "B": "聚落",
    "C": "自然實體",
    "D": "公共設施",
    "E": "街道",
}

# Matches the leading 序號/號次 of a data row: pure digits ("1", "307"),
# letter-prefixed IDs from the placename doc ("A001", "E2475"),
# or 增-prefixed supplements ("增1", "增4").
ID_PATTERN = re.compile(r"^(增?\d+|[A-Z]\d+)$")


def _cell_text(cell):
    parts = []
    for p in cell.iter("{%s}p" % NS_TEXT):
        parts.append("".join(p.itertext()))
    return "\n".join(parts).strip()


def _expand_row(row):
    """Return cell texts for one row, expanding number-columns-repeated.

    ODT files often pad the trailing edge of a row with hundreds of empty
    repeated cells; we cap the expansion at 200 to skip that padding.
    """
    cells = []
    for cell in row.findall("{%s}table-cell" % NS_TABLE):
        text = _cell_text(cell)
        rep = int(cell.get("{%s}number-columns-repeated" % NS_TABLE, "1"))
        if rep > 200:
            rep = 0
        cells.extend([text] * rep)
    return cells


def _read_odt_tables(list_zip_path):
    """Open *_list.zip → find the embedded ODT → parse content.xml → return tables."""
    with zipfile.ZipFile(list_zip_path) as outer:
        odt_name = next(n for n in outer.namelist() if n.lower().endswith(".odt"))
        with outer.open(odt_name) as odt_bytes:
            with zipfile.ZipFile(odt_bytes) as odt:
                with odt.open("content.xml") as f:
                    tree = ET.parse(f)
    return tree.getroot().findall(".//{%s}table" % NS_TABLE)


def _parse_transport_doc(list_zip_path, source):
    """Parse railways/tkmrt/thsrc/twtrip docs.

    railways/tkmrt have a 業者代碼 column and 10 data cols total
    (2 Taigi POJ variants + 漢字建議 + 說明; one Hakka 四縣腔 + 漢字建議 + 說明).
    thsrc/twtrip have 8 data cols (no 業者代碼, single Taigi 當地腔, single Hakka).
    """
    tables = _read_odt_tables(list_zip_path)
    if not tables:
        return []
    rows = tables[0].findall("{%s}table-row" % NS_TABLE)
    has_operator = source in ("railways", "tkmrt")
    expected = 10 if has_operator else 8

    out = []
    for row in rows:
        cells = _expand_row(row)
        if not cells or not ID_PATTERN.match(cells[0].strip()):
            continue
        cells = cells + [""] * (expected - len(cells))
        if has_operator:
            entry = {
                "來源": source,
                "序號": cells[0].strip(),
                "業者代碼": cells[1],
                "國語": cells[2],
                "臺灣台語_羅馬字": cells[3],
                "臺灣台語_漢字建議": cells[4],
                "臺灣台語_第二羅馬字": cells[5],
                "臺灣台語_說明": cells[6],
                "臺灣客語_羅馬字": cells[7],
                "臺灣客語_漢字建議": cells[8],
                "臺灣客語_說明": cells[9],
            }
        else:
            entry = {
                "來源": source,
                "序號": cells[0].strip(),
                "業者代碼": "",
                "國語": cells[1],
                "臺灣台語_羅馬字": cells[2],
                "臺灣台語_漢字建議": cells[3],
                "臺灣台語_第二羅馬字": "",
                "臺灣台語_說明": cells[4],
                "臺灣客語_羅馬字": cells[5],
                "臺灣客語_漢字建議": cells[6],
                "臺灣客語_說明": cells[7],
            }
        out.append(entry)
    return out


def _parse_placename_doc(list_zip_path, source):
    """Parse 地名計畫第2階段_地名清單. The doc has 3 tables; data is in the largest one."""
    tables = _read_odt_tables(list_zip_path)
    if not tables:
        return []
    main = max(tables, key=lambda t: len(t.findall("{%s}table-row" % NS_TABLE)))
    rows = main.findall("{%s}table-row" % NS_TABLE)

    out = []
    for row in rows:
        cells = _expand_row(row)
        if not cells or not ID_PATTERN.match(cells[0].strip()):
            continue
        cells = cells + [""] * (6 - len(cells))
        # Source columns: 序號, 地名, 臺灣客語拼音, 臺灣客語備註, 臺灣台語拼音, 臺灣台語備註
        out.append({
            "來源": source,
            "序號": cells[0].strip(),
            "業者代碼": "",
            "國語": cells[1],
            "臺灣台語_羅馬字": cells[4],
            "臺灣台語_漢字建議": "",
            "臺灣台語_第二羅馬字": "",
            "臺灣台語_說明": cells[5],
            "臺灣客語_羅馬字": cells[2],
            "臺灣客語_漢字建議": "",
            "臺灣客語_說明": cells[3],
        })
    return out


SOURCE_PARSERS = [
    ("railways_list.zip",  "railways",  _parse_transport_doc),
    ("tkmrt_list.zip",     "tkmrt",     _parse_transport_doc),
    ("thsrc_list.zip",     "thsrc",     _parse_transport_doc),
    ("twtrip_list.zip",    "twtrip",    _parse_transport_doc),
    ("placename_list.zip", "placename", _parse_placename_doc),
]


def _decode_zip_filename(member_name):
    """Match update_data.py's cp437→cp950 fallback for legacy-encoded zip entries."""
    base = os.path.basename(member_name)
    try:
        return base.encode("cp437").decode("cp950")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return base


def _build_audio_map(tangloo_dir, audio_zip_names):
    """For one source's audio zips, return {id_str: filename_after_extraction}.

    Mirrors update_data.py's extract_zip_flat: cp950-decode + strip leading
    `nan_` prefix, so the returned filenames match what's actually on disk
    under imtong/.
    """
    result = {}
    for zip_name in audio_zip_names:
        zip_path = tangloo_dir / zip_name
        if not zip_path.exists():
            continue
        with zipfile.ZipFile(zip_path) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                base = os.path.basename(member.filename)
                if not base:
                    continue
                if member.flag_bits & 0x800:
                    decoded = base
                else:
                    decoded = _decode_zip_filename(member.filename)
                if decoded.startswith("nan_"):
                    decoded = decoded[len("nan_"):]
                m = re.match(r"^([^_]+)_", decoded)
                if not m:
                    continue
                result.setdefault(m.group(1), decoded)
    return result


def _attach_audio(rows, tangloo_dir):
    maps = {src: _build_audio_map(tangloo_dir, zips) for src, zips in AUDIO_ZIPS.items()}
    for row in rows:
        row["音檔"] = maps.get(row["來源"], {}).get(row["序號"], "")


def _humanize_source(row):
    """Translate the internal 來源 key to a user-facing label.

    Transport docs map 1:1; placename rows split by 序號 prefix (A–E) or
    fall through to 增列地名 for 增-prefixed supplements and any non-prefixed
    IDs (the README documents 增列地名 as placename's catch-all label, so
    we keep output inside the documented enum even if upstream schema drifts).
    """
    src = row["來源"]
    if src in SOURCE_LABELS:
        return SOURCE_LABELS[src]
    if src == "placename":
        sid = row["序號"]
        if sid:
            label = PLACENAME_PREFIX_LABELS.get(sid[0])
            if label:
                return label
        return "增列地名"
    return src


def _write_csv(rows, csv_path):
    # utf-8-sig (BOM) so Excel auto-detects UTF-8 — same convention as KipSutian.
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for row in rows:
            w.writerow({col: row.get(col, "") for col in CSV_COLUMNS})


def _write_json(rows, json_path):
    nested = []
    for r in rows:
        nested.append({
            "來源": r["來源"],
            "序號": r["序號"],
            "業者代碼": r["業者代碼"],
            "國語": r["國語"],
            "臺灣台語": {
                "羅馬字": r["臺灣台語_羅馬字"],
                "第二羅馬字": r["臺灣台語_第二羅馬字"],
                "漢字建議": r["臺灣台語_漢字建議"],
                "說明": r["臺灣台語_說明"],
            },
            "臺灣客語": {
                "羅馬字": r["臺灣客語_羅馬字"],
                "漢字建議": r["臺灣客語_漢字建議"],
                "說明": r["臺灣客語_說明"],
            },
            "音檔": r["音檔"],
        })
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(nested, f, ensure_ascii=False, indent=2)


def convert_lists(tangloo_dir, bunji_dir):
    """Parse all 5 list ODTs from `tangloo_dir`, write merged CSV+JSON to `bunji_dir`."""
    tangloo_dir = Path(tangloo_dir)
    bunji_dir = Path(bunji_dir)
    bunji_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    for zip_name, source, parser in SOURCE_PARSERS:
        zip_path = tangloo_dir / zip_name
        if not zip_path.exists():
            print(f"  Skipping {zip_name} (not found in {tangloo_dir}).")
            continue
        rows = parser(zip_path, source)
        print(f"  {source}: parsed {len(rows)} rows from {zip_name}")
        all_rows.extend(rows)

    _attach_audio(all_rows, tangloo_dir)

    for row in all_rows:
        row["來源"] = _humanize_source(row)

    csv_path = bunji_dir / "KipTehomiaData.csv"
    json_path = bunji_dir / "KipTehomiaData.json"
    _write_csv(all_rows, csv_path)
    _write_json(all_rows, json_path)

    with_audio = sum(1 for r in all_rows if r["音檔"])
    print(f"  Wrote {len(all_rows)} rows to {csv_path.name} + {json_path.name} "
          f"({with_audio} with audio).")
