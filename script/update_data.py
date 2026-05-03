import os
import urllib.request
import zipfile
import datetime
import shutil
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

from convert_lists import convert_lists

# Constants
BASE_URL = "https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/"

FILES_TO_DOWNLOAD = [
    "railways_list.zip", "railways_m_mp3.zip",
    "tkmrt_list.zip", "tkmrt_m_mp3.zip",
    "thsrc_list.zip", "thsrc_m_mp3.zip",
    "twtrip_list.zip", "twtrip_m_mp3.zip",
    "placename_list.zip",
    "administrative_m_mp3.zip",
    "settlement_m_mp3.zip",
    "naturalentity_m_mp3.zip",
    "publicutilities_m_mp3.zip",
    "street_m_mp3.zip",
]

DOWNLOAD_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5
HTTP_TIMEOUT = 60

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
MANIFEST_FILE = PUBLIC_DIR / "manifest.json"

def get_timestamp_dir():
    """Generates a timestamped directory path (second resolution)."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return PUBLIC_DIR / timestamp

def head_last_modified(url):
    """Returns the Last-Modified header for url, or None if HEAD is unavailable."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}, method='HEAD')
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return r.getheader('Last-Modified')
    except Exception:
        return None

def download_file(url, target_path):
    """Downloads a file with retry. Returns (success_bool, last_modified_or_None)."""
    last_error = None
    for attempt in range(1, DOWNLOAD_RETRIES + 1):
        try:
            print(f"Downloading {url} (attempt {attempt}/{DOWNLOAD_RETRIES})...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                last_modified = r.getheader('Last-Modified')
                total_length = r.getheader('content-length')
                with open(target_path, 'wb') as f:
                    if total_length is None: # no content length header
                        f.write(r.read())
                    else:
                        dl = 0
                        total_length = int(total_length)
                        while True:
                            data = r.read(4096)
                            if not data:
                                break
                            dl += len(data)
                            f.write(data)
                            done = int(50 * dl / total_length)
                            sys.stdout.write(f"\r[{'=' * done}{' ' * (50-done)}] {dl/1024/1024:.2f} MB")
                            sys.stdout.flush()
                        if dl < total_length:
                            raise IOError(f"truncated download: got {dl} of {total_length} bytes")
                print() # Newline after progress bar
            return True, last_modified
        except Exception as e:
            last_error = e
            print(f"\nError downloading {url}: {e}")
            if attempt < DOWNLOAD_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)
    print(f"Giving up on {url} after {DOWNLOAD_RETRIES} attempts (last error: {last_error}).")
    return False, None

def calculate_file_hash(filepath):
    """Calculates the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def decode_zip_filename(member):
    """Decode a zip member's filename, honoring the ZIP UTF-8 (bit 11) flag.
    Always returns a single path component (no separators)."""
    raw = os.path.basename(member.filename)
    if member.flag_bits & 0x800:
        # ZIP spec says filename is UTF-8; round-tripping through cp437→cp950
        # would silently corrupt pure-ASCII names.
        decoded = raw
    else:
        try:
            decoded = raw.encode('cp437').decode('cp950')
        except (UnicodeEncodeError, UnicodeDecodeError):
            decoded = raw
    # Re-basename: belt-and-braces against any path separator that could
    # emerge from the decode (and against future encoding changes).
    return os.path.basename(decoded)

def extract_zip_flat(zip_path, extract_to):
    """Extracts files flat to extract_to. Raises on failure (no return value)."""
    print(f"Extracting {zip_path} to {extract_to} (flattened)...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        members = zip_ref.infolist()
        extracted_count = 0
        for member in members:
            if member.is_dir():
                continue

            filename = decode_zip_filename(member)
            if filename.startswith("nan_"):
                filename = filename[len("nan_"):]
            if not filename:
                continue

            target_path = os.path.join(extract_to, filename)

            with zip_ref.open(member) as source, open(target_path, "wb") as target:
                shutil.copyfileobj(source, target)

            extracted_count += 1
            if extracted_count % 100 == 0:
                 sys.stdout.write(f"\rExtracting: {extracted_count} files")
                 sys.stdout.flush()
        print(f"\rExtracted {extracted_count} files.")

def load_manifest():
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_manifest(data):
    # Write to a temp file and atomically rename so a crash mid-write can't
    # leave a half-written manifest that breaks every subsequent run.
    tmp = MANIFEST_FILE.with_suffix(MANIFEST_FILE.suffix + ".tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, MANIFEST_FILE)

def main():
    print("Starting update check...")

    current_manifest = load_manifest()
    cached_hashes = current_manifest.get("files", {})
    cached_last_modified = current_manifest.get("last_modified", {})
    latest_version_dir_name = current_manifest.get("latest_version_dir")

    # 1. HEAD pre-flight: avoid downloading anything if Last-Modified matches
    #    cached values for every file and the latest version dir is intact.
    if cached_last_modified and latest_version_dir_name:
        existing_dir = PUBLIC_DIR / latest_version_dir_name
        if existing_dir.exists():
            print("Probing source for changes (HEAD)...")
            head_inconclusive = False
            for filename in FILES_TO_DOWNLOAD:
                lm = head_last_modified(BASE_URL + filename)
                if lm is None:
                    print(f"  HEAD inconclusive for {filename}; falling back to full download")
                    head_inconclusive = True
                    break
                if lm != cached_last_modified.get(filename):
                    print(f"  Last-Modified changed for {filename}")
                    head_inconclusive = True
                    break
            if not head_inconclusive:
                print("No changes detected via HEAD. Using existing latest directory.")
                print(f"Data stored in: {existing_dir}")
                return

    # 2. Setup unique temp directory (avoids concurrent-run clobbering and
    #    leftovers from a prior crashed run).
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(tempfile.mkdtemp(prefix="temp_update_", dir=str(PUBLIC_DIR)))

    target_dir = None
    target_dir_was_created = False
    success = False

    try:
        # 3. Download all files to temp (with retry on transient errors).
        downloaded_hashes = {}
        downloaded_last_modified = {}
        for filename in FILES_TO_DOWNLOAD:
            url = BASE_URL + filename
            temp_path = temp_dir / filename
            ok, lm = download_file(url, temp_path)
            if not ok:
                print(f"Failed to download {filename}. Aborting.")
                sys.exit(1)
            downloaded_hashes[filename] = calculate_file_hash(temp_path)
            downloaded_last_modified[filename] = lm

        # 4. Compare hashes against the manifest.
        changes_detected = False
        if not cached_hashes:
            print("No existing manifest found. Proceeding with initial update...")
            changes_detected = True
        else:
            for filename, new_hash in downloaded_hashes.items():
                if new_hash != cached_hashes.get(filename):
                    print(f"Change detected in {filename}.")
                    changes_detected = True
                    break

        if not changes_detected:
            print("No changes detected in any files.")
            if latest_version_dir_name:
                existing_dir = PUBLIC_DIR / latest_version_dir_name
                if existing_dir.exists():
                    print(f"Using existing latest directory: {existing_dir}")
                    # Refresh Last-Modified so a future HEAD pre-flight can short-circuit.
                    new_manifest = dict(current_manifest)
                    new_manifest["last_modified"] = downloaded_last_modified
                    save_manifest(new_manifest)
                    target_dir = existing_dir
                else:
                    print(f"Existing directory {latest_version_dir_name} not found. Forcing creation of new one.")
                    changes_detected = True
            else:
                print("Latest version directory not defined in manifest. Forcing creation of new one.")
                changes_detected = True

        if changes_detected:
            print("Proceeding with update/creation of new folder...")

            # 5. Create timestamped version directory.
            target_dir = get_timestamp_dir()
            bunji_dir = target_dir / "bunji"
            imtong_dir = target_dir / "imtong"
            tangloo_dir = target_dir / "tangloo"

            bunji_dir.mkdir(parents=True, exist_ok=True)
            imtong_dir.mkdir(parents=True, exist_ok=True)
            tangloo_dir.mkdir(parents=True, exist_ok=True)
            target_dir_was_created = True
            print(f"Created version directory: {target_dir}")

            # 6. Move and extract. Any extraction error propagates to the
            #    except block, which removes the partial target_dir so a
            #    future run starts clean. *_list.zip stays in tangloo/ —
            #    convert_lists reads the embedded ODT directly from there.
            for filename in FILES_TO_DOWNLOAD:
                temp_path = temp_dir / filename
                tangloo_path = tangloo_dir / filename
                shutil.move(str(temp_path), str(tangloo_path))

                if filename.endswith("_mp3.zip"):
                    extract_zip_flat(tangloo_path, imtong_dir)

            # 7. Build merged bunji (CSV + JSON) from list ODTs in tangloo/.
            print("Building bunji from list documents...")
            convert_lists(tangloo_dir, bunji_dir)

            # 8. Manifest is written ONLY after every extraction succeeds.
            new_manifest = {
                "last_updated": datetime.datetime.now().isoformat(),
                "latest_version_dir": str(target_dir.name),
                "files": downloaded_hashes,
                "last_modified": downloaded_last_modified,
            }
            save_manifest(new_manifest)
            print("Updated manifest.json.")

        success = True

    except Exception as e:
        print(f"\nError during update: {e}")
        raise
    finally:
        # Removes a partial target_dir on any non-success exit (exception OR
        # KeyboardInterrupt/SystemExit), so the next run starts from clean state.
        if not success and target_dir_was_created and target_dir and target_dir.exists():
            print(f"Removing partial target directory: {target_dir}")
            shutil.rmtree(target_dir)
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    print("\nUpdate complete!")
    if target_dir:
        print(f"Data stored in: {target_dir}")

if __name__ == "__main__":
    main()
