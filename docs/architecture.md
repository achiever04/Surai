# System Architecture

## Overview
AI-Powered Multi-Camera Intelligence Platform with blockchain-verified evidence chain of custody and federated learning.

## Architecture Layers

### 1. Presentation Layer
- **Frontend**: React 18 with Tailwind CSS
- **Real-time Updates**: WebSocket connections for live feeds
- **Visualization**: Recharts for analytics dashboards

### 2. Application Layer (FastAPI)
- **API Gateway**: REST API with JWT authentication
- **Core Services**:
  - Camera Management Service
  - Detection Service
  - Watchlist Service
  - Evidence Service
  - Blockchain Service
  - Analytics Service

### 3. AI/ML Processing Layer
- **Face Detection**: MTCNN (lightweight, CPU-optimized)
- **Face Recognition**: InsightFace (ONNX runtime)
- **Emotion Detection**: DeepFace
- **Pose Estimation**: MediaPipe
- **Anti-Spoofing**: Silent-Face-Anti-Spoofing
- **Behavior Analysis**: Custom rules engine

### 4. Data Layer
- **PostgreSQL**: Metadata, user data, detections
- **Redis**: Caching, message queuing
- **IPFS**: Decentralized evidence storage
- **Blockchain**: Hyperledger Fabric for tamper-proof audit trail

### 5. Infrastructure Layer
- **Containerization**: Docker & Docker Compose
- **Camera Sources**: USB webcams, RTSP IP cameras, video files
- **Blockchain Network**: 2 organizations, 2 peers, 1 orderer

## Data Flow

1. Camera captures frame → Camera Manager
2. Frame processed → AI Detection Pipeline
3. Face detected → Matched against Watchlist
4. Detection created → Evidence stored (local + IPFS)
5. Evidence hash → Anchored to Blockchain
6. Alert sent → Notification Service
7. Operator reviews → Verification recorded
8. Audit trail → Immutable blockchain record

## Security Architecture

### Authentication & Authorization
- JWT tokens with role-based access control
- Roles: Admin, Operator, Auditor
- Password hashing with bcrypt

### Data Protection
- Evidence encryption at rest
- TLS/SSL for data in transit
- Blockchain for tamper-proof audit logs
- IPFS content addressing for integrity

### Privacy Preservation
- Federated learning for distributed training
- Differential privacy for model updates
- Secure aggregation protocols
- Local data processing (no raw data sharing)

## Scalability Considerations

### Horizontal Scaling
- Stateless FastAPI workers
- Load balancing with Nginx
- Redis pub/sub for distributed workers

### Performance Optimization
- Frame skipping (process every Nth frame)
- Motion detection to skip static scenes
- Lazy model loading
- ONNX runtime for CPU inference
- Connection pooling for databases

## Deployment Options

### Single Machine (Development)
- Docker Compose on local machine
- 8GB RAM minimum
- CPU-only inference

### Production Cluster
- Kubernetes orchestration
- Separate services for scaling
- GPU nodes for AI inference
- HA database setup
- Multi-region blockchain network

## Monitoring & Observability

### Metrics
- Camera health and FPS
- Detection throughput
- API response times
- Blockchain confirmation times

### Logging
- Structured logging with Loguru
- Centralized log aggregation
- Error tracking and alerting

### Audit Trail
- All operations logged to blockchain
- Chain of custody for evidence
- Operator actions tracked
- Immutable history