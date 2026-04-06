import os
import pathlib

# The root directory name
root_dir = "ai-surveillance-platform"

# List of all files to be created (relative to root)
files = [
    "README.md", ".env.example", ".env", ".gitignore", "requirements.txt", "docker-compose.yml", "setup.py",
    
    # Docs
    "docs/architecture.md", "docs/api_documentation.md", "docs/blockchain_integration.md", "docs/deployment_guide.md", "docs/user_manual.md",
    
    # Config
    "config/__init__.py", "config/settings.py", "config/database.py", "config/redis_config.py", 
    "config/blockchain_config.py", "config/camera_config.yaml", "config/model_config.yaml",
    
    # Blockchain - Fabric Network
    "blockchain/fabric-network/docker-compose-fabric.yml", "blockchain/fabric-network/configtx.yaml", "blockchain/fabric-network/crypto-config.yaml",
    "blockchain/fabric-network/scripts/generate_crypto.sh", "blockchain/fabric-network/scripts/start_network.sh", "blockchain/fabric-network/scripts/stop_network.sh",
    
    # Blockchain - Chaincode
    "blockchain/chaincode/evidence-contract/package.json", "blockchain/chaincode/evidence-contract/index.js",
    "blockchain/chaincode/evidence-contract/lib/evidence-contract.js", "blockchain/chaincode/evidence-contract/lib/evidence.js",
    "blockchain/chaincode/watchlist-contract/package.json", "blockchain/chaincode/watchlist-contract/index.js", # Placeholder for similar structure
    "blockchain/chaincode/fl-contract/package.json", "blockchain/chaincode/fl-contract/index.js", # Placeholder for similar structure
    
    # Blockchain - SDK
    "blockchain/sdk/__init__.py", "blockchain/sdk/fabric_client.py", "blockchain/sdk/chaincode_invoker.py",
    "blockchain/sdk/event_listener.py", "blockchain/sdk/utils.py",
    
    # Backend - App
    "backend/app/__init__.py", "backend/app/main.py",
    "backend/app/api/__init__.py", "backend/app/api/deps.py",
    "backend/app/api/v1/__init__.py", "backend/app/api/v1/router.py",
    
    # Backend - Endpoints
    "backend/app/api/v1/endpoints/__init__.py", "backend/app/api/v1/endpoints/auth.py", "backend/app/api/v1/endpoints/cameras.py",
    "backend/app/api/v1/endpoints/detections.py", "backend/app/api/v1/endpoints/watchlist.py", "backend/app/api/v1/endpoints/evidence.py",
    "backend/app/api/v1/endpoints/blockchain.py", "backend/app/api/v1/endpoints/analytics.py", "backend/app/api/v1/endpoints/federated_learning.py",
    
    # Backend - Core/DB/Models
    "backend/app/core/__init__.py", "backend/app/core/security.py", "backend/app/core/logging.py", "backend/app/core/exceptions.py",
    "backend/app/db/__init__.py", "backend/app/db/base.py", "backend/app/db/session.py", "backend/app/db/init_db.py",
    "backend/app/models/__init__.py", "backend/app/models/user.py", "backend/app/models/camera.py", "backend/app/models/detection.py",
    "backend/app/models/watchlist.py", "backend/app/models/evidence.py", "backend/app/models/blockchain_receipt.py", "backend/app/models/fl_model.py",
    
    # Backend - Schemas/Services/Utils
    "backend/app/schemas/__init__.py", "backend/app/schemas/user.py", "backend/app/schemas/camera.py", "backend/app/schemas/detection.py",
    "backend/app/schemas/watchlist.py", "backend/app/schemas/evidence.py", "backend/app/schemas/blockchain.py",
    "backend/app/services/__init__.py", "backend/app/services/camera_service.py", "backend/app/services/detection_service.py",
    "backend/app/services/watchlist_service.py", "backend/app/services/evidence_service.py", "backend/app/services/blockchain_service.py",
    "backend/app/services/analytics_service.py", "backend/app/services/notification_service.py",
    "backend/app/utils/__init__.py", "backend/app/utils/hashing.py", "backend/app/utils/ipfs_client.py", "backend/app/utils/helpers.py",
    
    # Backend - Tests
    "backend/tests/__init__.py", "backend/tests/conftest.py",
    
    # AI Engine
    "ai_engine/__init__.py",
    "ai_engine/models/__init__.py", "ai_engine/models/face_detector.py", "ai_engine/models/face_recognizer.py",
    "ai_engine/models/pose_estimator.py", "ai_engine/models/emotion_detector.py", "ai_engine/models/anti_spoof.py", "ai_engine/models/age_estimator.py",
    "ai_engine/pipelines/__init__.py", "ai_engine/pipelines/detection_pipeline.py", "ai_engine/pipelines/tracking_pipeline.py", "ai_engine/pipelines/behavior_analyzer.py",
    "ai_engine/preprocessing/__init__.py", "ai_engine/preprocessing/image_preprocessor.py", "ai_engine/preprocessing/video_preprocessor.py",
    "ai_engine/feature_extraction/__init__.py", "ai_engine/feature_extraction/face_embeddings.py", "ai_engine/feature_extraction/gait_features.py",
    "ai_engine/utils/__init__.py", "ai_engine/utils/model_loader.py", "ai_engine/utils/inference_optimizer.py",
    
    # Camera Integration
    "camera_integration/__init__.py", "camera_integration/camera_manager.py", "camera_integration/stream_processor.py",
    "camera_integration/rtsp_client.py", "camera_integration/webcam_client.py", "camera_integration/video_recorder.py",
    
    # Federated Learning
    "federated_learning/__init__.py", "federated_learning/fl_server.py", "federated_learning/fl_client.py",
    "federated_learning/model_aggregator.py", "federated_learning/model_versioning.py", "federated_learning/secure_aggregation.py",
    
    # Storage
    "storage/ipfs/__init__.py", "storage/ipfs/ipfs_manager.py",
    
    # Frontend - Config
    "frontend/package.json", "frontend/package-lock.json", "frontend/.env", "frontend/.gitignore",
    "frontend/public/index.html", "frontend/public/favicon.ico",
    
    # Frontend - Src
    "frontend/src/App.jsx", "frontend/src/index.jsx", "frontend/src/index.css",
    "frontend/src/components/common/Header.jsx", "frontend/src/components/common/Sidebar.jsx", "frontend/src/components/common/LoadingSpinner.jsx", "frontend/src/components/common/Alert.jsx",
    "frontend/src/components/camera/CameraGrid.jsx", "frontend/src/components/camera/CameraFeed.jsx", "frontend/src/components/camera/CameraControls.jsx",
    "frontend/src/components/detection/DetectionList.jsx", "frontend/src/components/detection/DetectionCard.jsx", "frontend/src/components/detection/DetectionModal.jsx",
    "frontend/src/components/watchlist/WatchlistManager.jsx", "frontend/src/components/watchlist/PersonCard.jsx", "frontend/src/components/watchlist/EnrollmentForm.jsx",
    "frontend/src/components/blockchain/BlockchainExplorer.jsx", "frontend/src/components/blockchain/TransactionList.jsx", "frontend/src/components/blockchain/ProvenanceViewer.jsx",
    "frontend/src/components/analytics/Dashboard.jsx", "frontend/src/components/analytics/Charts.jsx",
    
    # Frontend - Pages/Services/Hooks
    "frontend/src/pages/LoginPage.jsx", "frontend/src/pages/DashboardPage.jsx", "frontend/src/pages/CamerasPage.jsx", "frontend/src/pages/WatchlistPage.jsx",
    "frontend/src/pages/EvidencePage.jsx", "frontend/src/pages/AnalyticsPage.jsx", "frontend/src/pages/AuditPage.jsx",
    "frontend/src/services/api.js", "frontend/src/services/auth.js", "frontend/src/services/websocket.js", "frontend/src/services/blockchain.js",
    "frontend/src/hooks/useAuth.js", "frontend/src/hooks/useWebSocket.js", "frontend/src/hooks/useDetections.js",
    "frontend/src/context/AuthContext.jsx", "frontend/src/context/AppContext.jsx",
    "frontend/src/utils/constants.js", "frontend/src/utils/helpers.js",
    
    # Scripts
    "scripts/setup_environment.sh", "scripts/download_models.py", "scripts/init_database.py", "scripts/create_admin_user.py", "scripts/start_services.sh", "scripts/stop_services.sh",
    
    # Migrations
    "migrations/alembic/alembic.ini", "migrations/alembic/env.py", "migrations/alembic/script.py.mako",
]

# List of empty directories to create (for folders that contain no files yet or have .gitkeep)
empty_dirs = [
    "blockchain/fabric-network/organizations/org1/ca",
    "blockchain/fabric-network/organizations/org1/peers",
    "blockchain/fabric-network/organizations/org1/users",
    "blockchain/fabric-network/organizations/org2/ca",
    "blockchain/fabric-network/organizations/org2/peers",
    "blockchain/fabric-network/organizations/org2/users",
    "blockchain/fabric-network/channel-artifacts",
    "backend/tests/test_api", "backend/tests/test_services", "backend/tests/test_blockchain",
    "storage/local/evidence", "storage/models/pretrained", "storage/models/checkpoints",
    "migrations/alembic/versions",
    "logs/backend", "logs/ai_engine", "logs/blockchain", "logs/federated_learning",
    "data/watchlist", "data/embeddings", "data/temp"
]

def create_structure():
    print(f"Creating project structure for: {root_dir}")
    
    # Create Root
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    # Create Files (and their parent dirs)
    for file_path in files:
        full_path = os.path.join(root_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            pass # Create empty file

    # Create Empty Directories (add .gitkeep so git tracks them)
    for dir_path in empty_dirs:
        full_path = os.path.join(root_dir, dir_path)
        os.makedirs(full_path, exist_ok=True)
        with open(os.path.join(full_path, '.gitkeep'), 'w') as f:
            pass

    print("Structure created successfully!")
    print(f"Next step: cd {root_dir} && git init")

if __name__ == "__main__":
    create_structure()