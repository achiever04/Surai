"""
Notification service for alerts and notifications
"""
from typing import List, Dict, Any, Set
from datetime import datetime, timezone
import json
from fastapi import WebSocket
from loguru import logger


class NotificationService:
    def __init__(self):
        # Store active WebSocket connections
        self.active_connections: Set[WebSocket] = set()
    
    async def connect_websocket(self, websocket: WebSocket):
        """Register new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect_websocket(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_detection_alert(
        self,
        detection: Dict[str, Any],
        recipients: List[str]
    ):
        """Send real-time detection alert"""
        
        alert_message = {
            "type": "detection_alert",
            "data": detection,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": self._determine_severity(detection)
        }
        
        # Broadcast to all WebSocket clients
        await self._broadcast(alert_message)
        
        # Send email/SMS notifications
        for recipient in recipients:
            await self._send_email(recipient, alert_message)
    
    async def notify_watchlist_match(
        self,
        person_name: str,
        camera_location: str,
        confidence: float
    ):
        """Send watchlist match notification"""
        
        message = {
            "type": "watchlist_match",
            "person_name": person_name,
            "location": camera_location,
            "confidence": confidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "severity": "high"
        }
        
        await self._broadcast(message)
    
    async def notify_system_event(
        self,
        event_type: str,
        message: str,
        severity: str = "info"
    ):
        """Send system event notification"""
        
        notification = {
            "type": "system_event",
            "event_type": event_type,
            "message": message,
            "severity": severity,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self._broadcast(notification)

    async def broadcast_detection(self, detection_data: Dict[str, Any]):
        """Broadcast new detection to all connected clients"""
        message = {
            "type": "new_detection",
            "data": detection_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await self._broadcast(message)
    
    async def _broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected WebSocket clients"""
        
        if not self.active_connections:
            logger.debug("No active WebSocket connections for broadcast")
            return
        
        # Convert to JSON
        message_json = json.dumps(message)
        
        # Send to all connections
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect_websocket(connection)
        
        logger.info(f"Broadcast message to {len(self.active_connections)} clients")
    
    async def _send_email(self, recipient: str, message: Dict[str, Any]):
        """Send email notification (placeholder - implement with SMTP)"""
        
        # TODO: Implement actual email sending with SMTP
        # Example using smtplib:
        """
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText(json.dumps(message, indent=2))
        msg['Subject'] = f"Alert: {message.get('type')}"
        msg['From'] = "alerts@surveillance.local"
        msg['To'] = recipient
        
        with smtplib.SMTP('localhost') as server:
            server.send_message(msg)
        """
        
        logger.info(f"Email notification queued for {recipient}: {message.get('type')}")
    
    async def _send_sms(self, phone_number: str, message: str):
        """Send SMS notification (placeholder - implement with Twilio)"""
        
        # TODO: Implement SMS with Twilio or similar service
        """
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=message,
            from_='+1234567890',
            to=phone_number
        )
        """
        
        logger.info(f"SMS notification queued for {phone_number}")
    
    def _determine_severity(self, detection: Dict[str, Any]) -> str:
        """Determine alert severity"""
        
        detection_type = detection.get("detection_type")
        
        if detection_type in ["face_match", "intrusion"]:
            return "high"
        elif detection_type in ["suspicious_behavior", "loitering"]:
            return "medium"
        else:
            return "low"


# Global notification service instance
notification_service = NotificationService()