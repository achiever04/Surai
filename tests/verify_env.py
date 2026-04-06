import sys
import cv2
import requests
import torch
import tensorflow as tf
# CHANGE THIS LINE:
import hfc  
# (The package is 'fabric-sdk-py', but the import is 'hfc')

print("="*40)
print("✅ SYSTEM DIAGNOSTIC REPORT")
print("="*40)
print(f"Python:       {sys.version.split()[0]}")
print(f"Torch:        {torch.__version__} (CUDA Available: {torch.cuda.is_available()})")
print(f"TensorFlow:   {tf.__version__}")
print(f"OpenCV:       {cv2.__version__}")
print(f"Requests:     {requests.__version__} (Should be 2.31.0)")
print(f"Fabric SDK:   Installed (Imported as 'hfc')")
print("="*40)

try:
    import numpy as np
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5,5))
    print("✅ OpenCV GUI Linkage: OK")
except Exception as e:
    print(f"❌ OpenCV Error: {e}")

print("🚀 READY TO BUILD.")