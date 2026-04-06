export const API_BASE_URL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`;
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export const DETECTION_TYPES = {
  FACE_MATCH: 'face_match',
  SUSPICIOUS_BEHAVIOR: 'suspicious_behavior',
  EMOTION_ALERT: 'emotion_alert',
  LOITERING: 'loitering',
  INTRUSION: 'intrusion'
};

export const RISK_LEVELS = {
  LOW: 'low',
  MEDIUM: 'medium',
  HIGH: 'high',
  CRITICAL: 'critical'
};

export const USER_ROLES = {
  ADMIN: 'admin',
  OPERATOR: 'operator',
  AUDITOR: 'auditor'
};