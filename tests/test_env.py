import sys

print("--- TESTING ENVIRONMENT ---")

# 1. Test AI Engine (Torch + InsightFace)
try:
    import torch
    import insightface
    print(f"✅ AI Engine Loaded: Torch {torch.__version__}, InsightFace {insightface.__version__}")
except ImportError as e:
    print(f"❌ AI Engine Failed: {e}")

# 2. Test Blockchain SDK (Fabric)
try:
    from hfc.fabric import Client
    print("✅ Blockchain SDK Loaded: Hyperledger Fabric Client is ready")
except ImportError as e:
    print(f"❌ Blockchain SDK Failed: {e}")

# 3. Test Requests (The conflicting library)
try:
    import requests
    print(f"✅ Network Lib Loaded: Requests {requests.__version__}")
except ImportError as e:
    print(f"❌ Network Lib Failed: {e}")
