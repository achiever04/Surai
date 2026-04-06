# API Documentation

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints except `/auth/login` require Bearer token authentication.

**Header:**
```
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### POST `/auth/login`
Login and get access token.

**Request:**
```json
{
  "username": "admin",
  "password": "admin123"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### GET `/auth/me`
Get current user information.

**Response:**
```json
{
  "id": 1,
  "username": "admin",
  "email": "admin@example.com",
  "full_name": "Administrator",
  "role": "admin",
  "is_active": true
}
```

---

## Camera Endpoints

### GET `/cameras`
Get all cameras.

**Query Parameters:**
- `skip` (int): Pagination offset
- `limit` (int): Max results (default: 100)
- `is_active` (bool): Filter by active status

**Response:**
```json
[
  {
    "id": 1,
    "name": "Main Entrance",
    "source_type": "webcam",
    "source_url": "0",
    "location": "Building A",
    "is_active": true,
    "is_online": true,
"health_status": "healthy",
"resolution_width": 1280,
"resolution_height": 720,
"fps": 10
}
]

### POST `/cameras`
Create new camera.

**Request:**
```json
{
  "name": "Parking Camera",
  "source_type": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream",
  "location": "Parking Lot",
  "resolution_width": 1920,
  "resolution_height": 1080,
  "fps": 15
}
```

### POST `/cameras/{camera_id}/start`
Start camera stream processing.

### POST `/cameras/{camera_id}/stop`
Stop camera stream processing.

---

## Detection Endpoints

### GET `/detections`
Get all detections with filtering.

**Query Parameters:**
- `skip` (int): Pagination offset
- `limit` (int): Max results
- `camera_id` (int): Filter by camera
- `detection_type` (string): Filter by type
- `is_verified` (bool): Filter by verification status
- `start_date` (datetime): Filter start date
- `end_date` (datetime): Filter end date

**Response:**
```json
[
  {
    "id": 1,
    "event_id": "evt_20250125_143022_1",
    "camera_id": 1,
    "detection_type": "face_match",
    "confidence": 0.95,
    "timestamp": "2025-01-25T14:30:22Z",
    "matched_person_id": 5,
    "emotion": "neutral",
    "is_verified": false
  }
]
```

### GET `/detections/{detection_id}`
Get detection details.

### PATCH `/detections/{detection_id}`
Update detection (operator action).

**Request:**
```json
{
  "operator_action": "verified",
  "is_verified": true,
  "notes": "Confirmed identity"
}
```

---

## Watchlist Endpoints

### GET `/watchlist`
Get all watchlist persons.

### POST `/watchlist`
Enroll new person in watchlist.

**Request (multipart/form-data):**
person_data: {
"person_id": "P001",
"name": "John Doe",
"category": "missing",
"risk_level": "high",
"age": 35,
"gender": "male"
}
photos: [file1.jpg, file2.jpg]

### PUT `/watchlist/{person_id}`
Update watchlist person.

### DELETE `/watchlist/{person_id}`
Remove person from watchlist.

---

## Analytics Endpoints

### GET `/analytics/dashboard`
Get dashboard statistics.

**Response:**
```json
{
  "total_cameras": 4,
  "active_cameras": 3,
  "detections_24h": 127,
  "total_detections": 1543,
  "watchlist_persons": 15,
  "unverified_detections": 23
}
```

### GET `/analytics/trends`
Get detection trends over time.

**Query Parameters:**
- `days` (int): Number of days (default: 7)

---

## Blockchain Endpoints

### POST `/blockchain/provenance`
Get evidence provenance from blockchain.

**Request:**
```json
{
  "event_id": "evt_20250125_143022_1"
}
```

### POST `/blockchain/verify/{event_id}`
Verify evidence integrity using blockchain.

---

## Error Responses

All endpoints return standard error responses:
```json
{
  "detail": "Error message here",
  "type": "ResourceNotFoundError"
}
```

**HTTP Status Codes:**
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `500`: Internal Server Error