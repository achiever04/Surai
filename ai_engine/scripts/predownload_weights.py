"""
Pre-download AI model weights to prevent network delays during startup.

Run this script ONCE after initial setup:
    python -m ai_engine.scripts.predownload_weights

This ensures all model weights are cached locally so the server
doesn't need to download them during model initialization.
"""
import os
import sys


def predownload_deepface_weights():
    """Pre-download DeepFace model weights to ~/.deepface/weights/"""
    print("📦 Pre-downloading DeepFace weights...")
    try:
        os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '-1')
        
        from deepface import DeepFace
        import numpy as np
        import cv2
        
        # Create a dummy face image
        dummy = np.zeros((224, 224, 3), dtype=np.uint8)
        dummy[50:200, 50:200] = 128  # Gray face-sized region
        
        # Trigger age model download
        print("  → Downloading age model...")
        try:
            DeepFace.analyze(dummy, actions=['age'], enforce_detection=False, silent=True)
            print("  ✅ Age model cached")
        except Exception as e:
            print(f"  ⚠️ Age model: {e}")
        
        # Trigger emotion model download
        print("  → Downloading emotion model...")
        try:
            DeepFace.analyze(dummy, actions=['emotion'], enforce_detection=False, silent=True)
            print("  ✅ Emotion model cached")
        except Exception as e:
            print(f"  ⚠️ Emotion model: {e}")
        
        print("✅ DeepFace weights pre-downloaded")
    except ImportError:
        print("⚠️ DeepFace not installed, skipping")


def predownload_insightface_models():
    """Pre-download InsightFace buffalo_l model pack."""
    print("📦 Checking InsightFace models...")
    try:
        model_dir = os.path.expanduser("~/.insightface/models/buffalo_l")
        expected_files = ['1k3d68.onnx', '2d106det.onnx', 'det_10g.onnx', 'genderage.onnx', 'w600k_r50.onnx']
        
        all_present = all(
            os.path.exists(os.path.join(model_dir, f)) for f in expected_files
        )
        
        if all_present:
            print("  ✅ InsightFace buffalo_l models already cached")
        else:
            print("  → Downloading InsightFace buffalo_l...")
            from insightface.app import FaceAnalysis
            app = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
            app.prepare(ctx_id=-1, det_size=(640, 640))
            print("  ✅ InsightFace models cached")
    except ImportError:
        print("⚠️ InsightFace not installed, skipping")
    except Exception as e:
        print(f"⚠️ InsightFace: {e}")


def predownload_fer_model():
    """Pre-download FER emotion model."""
    print("📦 Checking FER model...")
    try:
        from fer import FER
        detector = FER(mtcnn=False)
        print("  ✅ FER model cached")
    except ImportError:
        print("⚠️ FER not installed, skipping")
    except Exception as e:
        print(f"⚠️ FER: {e}")


def main():
    print("=" * 60)
    print("AI Surveillance - Model Weight Pre-Download")
    print("=" * 60)
    print()
    
    predownload_insightface_models()
    print()
    predownload_deepface_weights()
    print()
    predownload_fer_model()
    
    print()
    print("=" * 60)
    print("✅ All model weights pre-downloaded!")
    print("   Subsequent server starts will be faster.")
    print("=" * 60)


if __name__ == "__main__":
    main()
