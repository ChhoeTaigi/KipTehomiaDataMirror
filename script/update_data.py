import os
import urllib.request
import zipfile
import datetime
import shutil
import hashlib
import json
import sys
from pathlib import Path

# Constants
BASE_URL = "https://language.moe.gov.tw/001/Upload/Files/site_content/M0001/mhigeonames/"

FILES_TO_DOWNLOAD = [
    "railways_list.zip", "railways_m_wav.zip", "railways_m_mp3.zip",
    "tkmrt_list.zip", "tkmrt_m_wav.zip", "tkmrt_m_mp3.zip",
    "thsrc_list.zip", "thsrc_m_wav.zip", "thsrc_m_mp3.zip",
    "twtrip_list.zip", "twtrip_m_wav.zip", "twtrip_m_mp3.zip",
    "placename_list.zip",
    "administrative_m_mp3.zip", "administrative_m_wav.zip",
    "settlement_m_mp3.zip", "settlement_m_wav.zip",
    "naturalentity_m_mp3.zip", "naturalentity_m_wav.zip",
    "publicutilities_m_mp3.zip", "publicutilities_m_wav.zip",
    "street_m_mp3.zip", "street_m_wav.zip"
]

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
MANIFEST_FILE = PUBLIC_DIR / "manifest.json"

def get_timestamp_dir():
    """Generates a timestamped directory path."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    return PUBLIC_DIR / timestamp

def download_file(url, target_path):
    """Downloads a file from a URL to a target path with progress indication."""
    print(f"Downloading {url} to {target_path}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as r:
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
            print() # Newline after progress bar
    except Exception as e:
        print(f"\nError downloading {url}: {e}")
        return False
    return True

def calculate_file_hash(filepath):
    """Calculates the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def extract_zip_flat(zip_path, extract_to):
    """Extracts all files from a zip to the target directory, ignoring internal folder structure."""
    print(f"Extracting {zip_path} to {extract_to} (flattened)...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            members = zip_ref.infolist()
            extracted_count = 0
            for member in members:
                if member.is_dir():
                    continue
                
                # Get just the filename, ignoring the path in the zip
                raw_filename = os.path.basename(member.filename)
                try:
                    filename = raw_filename.encode('cp437').decode('big5')
                except (UnicodeEncodeError, UnicodeDecodeError):
                    filename = raw_filename
                    
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
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return False
    return True

def load_manifest():
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_manifest(data):
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    print("Starting update check...")
    
    # 1. Setup Temp Directory
    temp_dir = PUBLIC_DIR / "temp_update"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded_hashes = {}
    
    try:
        # 2. Download all files to temp
        for filename in FILES_TO_DOWNLOAD:
            url = BASE_URL + filename
            temp_path = temp_dir / filename
            if not download_file(url, temp_path):
                print(f"Failed to download {filename}. Aborting.")
                shutil.rmtree(temp_dir)
                return
            downloaded_hashes[filename] = calculate_file_hash(temp_path)
            
        # 3. Check Manifest
        current_manifest = load_manifest()
        current_hashes = current_manifest.get("files", {})
        
        changes_detected = False
        if not current_hashes:
            print("No existing manifest found. Proceeding with initial update...")
            changes_detected = True
        else:
            for filename, new_hash in downloaded_hashes.items():
                old_hash = current_hashes.get(filename)
                if new_hash != old_hash:
                    print(f"Change detected in {filename}.")
                    changes_detected = True
                    break
        
        target_dir = None
        
        if not changes_detected:
            print("No changes detected in any files.")
            latest_version_dir_name = current_manifest.get("latest_version_dir")
            if latest_version_dir_name:
                target_dir = PUBLIC_DIR / latest_version_dir_name
                if target_dir.exists():
                     print(f"Using existing latest directory: {target_dir}")
                else:
                    print(f"Existing directory {latest_version_dir_name} not found. Forcing creation of new one.")
                    changes_detected = True
            else:
                print("Latest version directory not defined in manifest. Forcing creation of new one.")
                changes_detected = True

        if changes_detected:
            print("Proceeding with update/creation of new folder...")
            
            # 4. Create Timestamp Directory
            target_dir = get_timestamp_dir()
            list_dir = target_dir / "list"
            audio_mp3_dir = target_dir / "audio_mp3"
            audio_wav_dir = target_dir / "audio_wav"
            tangloo_dir = target_dir / "tangloo"
            
            list_dir.mkdir(parents=True, exist_ok=True)
            audio_mp3_dir.mkdir(parents=True, exist_ok=True)
            audio_wav_dir.mkdir(parents=True, exist_ok=True)
            tangloo_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created version directory: {target_dir}")

            # 5. Move/Process Files
            for filename in FILES_TO_DOWNLOAD:
                temp_path = temp_dir / filename
                tangloo_path = tangloo_dir / filename
                shutil.move(str(temp_path), str(tangloo_path))
                
                if filename.endswith("_list.zip"):
                    extract_zip_flat(tangloo_path, list_dir)
                elif filename.endswith("_mp3.zip"):
                    extract_zip_flat(tangloo_path, audio_mp3_dir)
                elif filename.endswith("_wav.zip"):
                    extract_zip_flat(tangloo_path, audio_wav_dir)
                
            # 6. Update Manifest
            new_manifest = {
                "last_updated": datetime.datetime.now().isoformat(),
                "latest_version_dir": str(target_dir.name),
                "files": downloaded_hashes
            }
            save_manifest(new_manifest)
            print("Updated manifest.json.")

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    print("\nUpdate complete!")
    print(f"Data stored in: {target_dir}")

if __name__ == "__main__":
    main()
