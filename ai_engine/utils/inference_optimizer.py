import torch
import onnxruntime as ort

class CPUOptimizer:
    @staticmethod
    def optimize_torch_inference():
        # Use Intel MKL optimizations
        torch.set_num_threads(4)  # Ryzen 5 typically has 6 cores, use 4
        torch.set_num_interop_threads(2)
        
    @staticmethod
    def create_onnx_session(model_path):
        # CPU-optimized ONNX session
        session_options = ort.SessionOptions()
        session_options.intra_op_num_threads = 4
        session_options.inter_op_num_threads = 2
        session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        return ort.InferenceSession(
            model_path,
            sess_options=session_options,
            providers=['CPUExecutionProvider']
        )