"""
Download YOLOv8-nano model for weapon detection

This script downloads the YOLOv8-nano model which will be used
for real-time weapon and object detection.
"""
from ultralytics import YOLO
from loguru import logger

def download_yolo_model():
    """Download YOLOv8-nano model"""
    try:
        logger.info("Downloading YOLOv8-nano model...")
        
        # This will automatically download yolov8n.pt on first use
        model = YOLO('yolov8n.pt')
        
        logger.info("YOLOv8-nano model downloaded successfully!")
        logger.info(f"Model saved to: {model.ckpt_path}")
        
        # Test the model
        logger.info("Testing model...")
        import numpy as np
        test_frame = np.zeros((640, 640, 3), dtype=np.uint8)
        results = model(test_frame, verbose=False)
        
        logger.info("Model test successful!")
        logger.info(f"Model can detect {len(model.names)} classes")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to download YOLO model: {e}")
        return False

if __name__ == "__main__":
    success = download_yolo_model()
    if success:
        print("\n✅ YOLOv8-nano model ready for weapon detection!")
    else:
        print("\n❌ Failed to download model. Please check your internet connection.")
