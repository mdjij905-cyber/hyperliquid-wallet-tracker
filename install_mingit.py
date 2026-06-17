import os
import sys
import zipfile
import requests

URL = "https://github.com/git-for-windows/git/releases/download/v2.54.0.windows.1/MinGit-2.54.0-64-bit.zip"
DEST_DIR = os.path.join(os.getcwd(), "git")
ZIP_FILE = "mingit.zip"

def download_file(url, local_filename):
    print(f"Downloading {url}...")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download complete.")

def extract_zip(zip_path, extract_to):
    print(f"Extracting {zip_path} to {extract_to}...")
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete.")

def main():
    if not os.path.exists(DEST_DIR):
        download_file(URL, ZIP_FILE)
        extract_zip(ZIP_FILE, DEST_DIR)
        if os.path.exists(ZIP_FILE):
            os.remove(ZIP_FILE)
    else:
        print("MinGit already downloaded.")

    git_path = os.path.join(DEST_DIR, "cmd", "git.exe")
    if os.path.exists(git_path):
        print(f"MinGit verified successfully at {git_path}")
        import subprocess
        res = subprocess.run([git_path, "--version"], capture_output=True, text=True)
        print("Git version:", res.stdout.strip())
    else:
        print("Failed to find git.exe after extraction.")

if __name__ == "__main__":
    main()
