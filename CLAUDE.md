# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Data mirror for the Taiwan Ministry of Education's Taiwanese Place Names (教育部以本土語言標注臺灣地名計畫). Part of the ChhoeTaigi project. The repo downloads list data and audio zips, and hosts everything via GitHub Pages.

Licensed under CC BY 3.0 TW — the data cannot be modified (derivative works prohibited).

## Commands

```bash
# Run the full update pipeline (downloads from language.moe.gov.tw, checks for changes via SHA256 hashes, extracts data)
cd script && python update_data.py
```

Dependencies: pure Python stdlib (no `pip install` needed).

## Architecture

### Data Pipeline (`script/`)

1. **`update_data.py`** — Main entry point. Downloads files from language.moe.gov.tw, compares SHA256 hashes against `public/manifest.json` to detect changes, creates a timestamped version directory under `public/`, extracts audio zips into `imtong/`, and invokes `convert_lists` to build `bunji/`.
2. **`convert_lists.py`** — Parses the 5 ODT documents inside the `*_list.zip` archives in `tangloo/`, attaches per-source audio filenames, and writes a merged `bunji/KipTehomiaData.csv` (UTF-8 with BOM) and `bunji/KipTehomiaData.json` (UTF-8, nested).

### Data Layout (`public/`)

```
public/
  manifest.json              # Tracks latest version and file hashes
  {YYYYMMDD-HHMMSS}/         # Timestamped version directory
    bunji/                    # Merged CSV + JSON of all place names
      KipTehomiaData.csv
      KipTehomiaData.json
    imtong/                   # Flat directory of all mp3 audio files
    tangloo/                  # Original downloads (zips) — gitignored
```

### Hosting

- `index.md` is the GitHub Pages landing page
- `.nojekyll` disables Jekyll processing
- Audio files are served directly from `public/{version}/`

## Important Rules

- **`README.md` and `index.md` must stay in sync.** They have identical content. When updating version references or any other content in one, always update the other to match.

## Terminology (Taiwanese Hokkien)

- **bunji** (文字) — text data
- **imtong** (音通) — audio
- **tangloo** (檔路) — file storage / archives
- **tehomia** (地號名) — place names
