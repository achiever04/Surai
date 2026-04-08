import argparse
from ultralytics import YOLO

def export_model(model_name: str, device_type: str):
    """
    Export PyTorch trained YOLOv8 model into optimized runtime representations.
    
    device_type: 
      - 'gpu': Exports to TensorRT (Engine) with FP16 Half-Precision mapping.
      - 'cpu': Exports to ONNX with INT8 dynamic Quantization built in.
    """
    try:
        model = YOLO(model_name)
    except Exception as e:
        print(f"Failed to load model {model_name}: {e}")
        return
        
    print(f"Loaded {model_name} successfully.")
    
    if device_type == 'gpu':
        print(f"Exporting {model_name} to NVIDIA TensorRT FP16...")
        # Half=True compresses 32-bit floats to 16, slicing memory footprint by 50%
        # without losing spatial mapping accuracy.
        model.export(format='engine', dynamic=True, half=True, simplify=True)
        print("Done. Model will now utilize CUDA/TensorRT acceleration native.")
        
    elif device_type == 'cpu':
        print(f"Exporting {model_name} to ONNX INT8...")
        # INT8 drastically reduces model weight density for CPU inferencing
        # Requires onnxruntime to be installed natively
        model.export(format='onnx', int8=True, dynamic=True, simplify=True)
        print("Done. Model is calibrated for CPU-bound OpenVINO performance.")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize SurAI AI Models for Real-Time throughput")
    parser.add_argument("--model", type=str, default="yolov8n-pose.pt", help="Path to PyTorch model")
    parser.add_argument("--device", type=str, choices=['cpu', 'gpu'], default='cpu', help="Target Hardware")
    
    args = parser.parse_args()
    export_model(args.model, args.device)
