# GEMINI.md

This file provides guidance to Gemini CLI when working with code in this repository.

## Project Overview

Data mirror for the Taiwan Ministry of Education's Taiwanese Place Names (教育部以本土語言標注臺灣地名計畫). Part of the ChhoeTaigi project. The repo downloads list data and audio zips, and hosts everything via GitHub Pages.

Licensed under CC BY 3.0 TW — the data cannot be modified (derivative works prohibited).

## Commands

```bash
# Run the full update pipeline (downloads from language.moe.gov.tw, checks for changes via SHA256 hashes, extracts data)
cd script && python update_data.py
```

Dependencies: `requests`. Install with `pip install requests`.

## Architecture

### Data Pipeline (`script/`)

1. **`update_data.py`** — Main entry point. Downloads files from language.moe.gov.tw, compares SHA256 hashes against `public/manifest.json` to detect changes, creates a timestamped version directory under `public/`, and extracts zip contents.

### Data Layout (`public/`)

```
public/
  manifest.json              # Tracks latest version and file hashes
  {YYYYMMDD-HHMM}/           # Timestamped version directory
    list/                     # Extracted list files
    audio_mp3/                # Extracted mp3 audio files
    audio_wav/                # Extracted wav audio files
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
