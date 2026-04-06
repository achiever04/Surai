from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Surveillance Platform"
    VERSION: str = "1.0.0"
    
    # Security
    SECRET_KEY: str  # Required — must be set in .env
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Database
    POSTGRES_USER: str = "surveillance_user"
    POSTGRES_PASSWORD: str  # Required — must be set in .env
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "surveillance_db"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = ""
    
    # IPFS
    IPFS_API: str = "/dns/localhost/tcp/5001/http"
    IPFS_GATEWAY: str = "http://localhost:8080"
    
    # Blockchain
    FABRIC_NETWORK_PATH: str = "./blockchain/fabric-network"
    FABRIC_ORG1_MSP: str = "Org1MSP"
    FABRIC_ORG2_MSP: str = "Org2MSP"
    CHANNEL_NAME: str = "surveillance-channel"
    EVIDENCE_CHAINCODE: str = "evidence-contract"
    WATCHLIST_CHAINCODE: str = "watchlist-contract"
    
    # AI Models
    FACE_DETECTION_MODEL: str = "mtcnn"
    FACE_RECOGNITION_MODEL: str = "insightface"
    CONFIDENCE_THRESHOLD: float = 0.7
    
    # Camera
    MAX_CAMERAS: int = 4
    FRAME_RATE: int = 10 
    
    # --- ADDED MISSING FIELDS HERE ---
    PROCESS_EVERY_NTH_FRAME: int = 3
    VIDEO_RESOLUTION_WIDTH: int = 1280
    VIDEO_RESOLUTION_HEIGHT: int = 1280
    
    # Feature Flags
    EMOTION_DETECTION_ENABLED: bool = True
    POSE_ESTIMATION_ENABLED: bool = True
    ANTI_SPOOF_ENABLED: bool = True
    AGE_ESTIMATION_ENABLED: bool = False
    # ----------------------------------

    # Storage
    EVIDENCE_RETENTION_DAYS: int = 30
    MAX_EVIDENCE_SIZE_MB: int = 500
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Added this to prevent crashes on future extra fields

settings = Settings()