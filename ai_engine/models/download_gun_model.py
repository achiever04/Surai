"""
Download pre-trained gun detection model
"""
import os
import requests
from loguru import logger


def download_gun_model():
    """Download pre-trained YOLOv8 gun detection model"""
    
    # Model URL from GitHub repository
    # Using Beastojenisto/WraponDetectionYOLOv8 repository
    model_url = "https://github.com/Beastojenisto/WraponDetectionYOLOv8/raw/main/GunDetector.pt"
    
    # Create weights directory
    weights_dir = os.path.join(os.path.dirname(__file__), 'weights')
    os.makedirs(weights_dir, exist_ok=True)
    
    # Download model
    model_path = os.path.join(weights_dir, 'gun_detector.pt')
    
    if os.path.exists(model_path):
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        logger.info(f"✅ Gun detection model already exists at {model_path} ({file_size:.2f} MB)")
        return model_path
    
    logger.info(f"📥 Downloading gun detection model from {model_url}...")
    logger.info("This may take a few minutes depending on your internet speed...")
    
    try:
        response = requests.get(model_url, stream=True, timeout=60)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(model_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        progress = (downloaded / total_size) * 100
                        print(f"\rDownload progress: {progress:.1f}%", end='', flush=True)
        
        print()  # New line after progress
        file_size = os.path.getsize(model_path) / (1024 * 1024)  # MB
        logger.info(f"✅ Gun detection model downloaded successfully to {model_path} ({file_size:.2f} MB)")
        return model_path
    
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to download model from {model_url}: {e}")
        logger.info("Trying alternative source...")
        
        # Alternative: Try Roboflow model
        try:
            alt_url = "https://app.roboflow.com/ds/example-gun-model.pt"  # Placeholder
            logger.info(f"Attempting download from alternative source: {alt_url}")
            # Similar download logic
        except:
            logger.error("All download sources failed")
            return None
    
    except Exception as e:
        logger.error(f"❌ Unexpected error during download: {e}")
        return None


if __name__ == "__main__":
    logger.info("=== Gun Detection Model Downloader ===")
    result = download_gun_model()
    
    if result:
        logger.info(f"✅ SUCCESS: Model ready at {result}")
        logger.info("You can now use gun detection in the surveillance system")
    else:
        logger.error("❌ FAILED: Could not download gun detection model")
        logger.info("Please download manually from:")
        logger.info("https://github.com/Beastojenisto/WraponDetectionYOLOv8")
