"""
Download pretrained AI models
"""
import os
import urllib.request
import zipfile
from pathlib import Path

MODEL_DIR = Path("storage/models/pretrained")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODELS = {
    "insightface_buffalo_l": {
        "url": "https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_l.zip",
        "path": MODEL_DIR / "buffalo_l.zip"
    },
    # Add more models as needed
}

def download_file(url, destination):
    """Download file with progress"""
    print(f"Downloading {url}...")
    
    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        print(f"\rProgress: {percent}%", end="")
    
    urllib.request.urlretrieve(url, destination, progress_hook)
    print("\nDownload complete!")

def extract_zip(zip_path, extract_to):
    """Extract zip file"""
    print(f"Extracting {zip_path}...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    print("Extraction complete!")
    os.remove(zip_path)

def main():
    print("=" * 50)
    print("Downloading Pretrained Models")
    print("=" * 50)
    
    for name, info in MODELS.items():
        print(f"\n[{name}]")
        
        if info["path"].exists():
            print("Already downloaded, skipping...")
            continue
        
        download_file(info["url"], info["path"])
        
        if info["path"].suffix == ".zip":
            extract_zip(info["path"], MODEL_DIR)
    
    print("\n" + "=" * 50)
    print("All models downloaded successfully!")
    print("=" * 50)

if __name__ == "__main__":
    main()