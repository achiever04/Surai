"""
Analytics service for dashboard statistics and insights
"""
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.detection import Detection
from app.models.camera import Camera
from app.models.watchlist import WatchlistPerson

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Get main dashboard statistics
        """
        # Total cameras
        camera_count_result = await self.db.execute(
            select(func.count(Camera.id))
        )
        total_cameras = camera_count_result.scalar() or 0
        
        # Active cameras
        active_cameras_result = await self.db.execute(
            select(func.count(Camera.id)).where(Camera.is_active == True)
        )
        active_cameras = active_cameras_result.scalar() or 0
        
        # Total detections (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        detections_24h_result = await self.db.execute(
            select(func.count(Detection.id))
            .where(Detection.timestamp >= yesterday)
        )
        detections_24h = detections_24h_result.scalar() or 0
        
        # Total detections (all time)
        total_detections_result = await self.db.execute(
            select(func.count(Detection.id))
        )
        total_detections = total_detections_result.scalar() or 0
        
        # Watchlist persons
        watchlist_count_result = await self.db.execute(
            select(func.count(WatchlistPerson.id))
            .where(WatchlistPerson.is_active == True)
        )
        watchlist_count = watchlist_count_result.scalar() or 0
        
        # Unverified detections
        unverified_result = await self.db.execute(
            select(func.count(Detection.id))
            .where(Detection.is_verified == False)
        )
        unverified_count = unverified_result.scalar() or 0
        
        # High priority alerts (last 24 hours)
        high_priority_result = await self.db.execute(
            select(func.count(Detection.id))
            .where(Detection.timestamp >= yesterday)
            .where(Detection.detection_type.in_(["watchlist_match", "weapon_detected", "spoof_attempt"]))
        )
        high_priority = high_priority_result.scalar() or 0
        
        # Calculate peak activity hour (most detections)
        peak_hour = "N/A"
        try:
            peak_hour_result = await self.db.execute(
                select(
                    func.extract('hour', Detection.timestamp).label('hour'),
                    func.count(Detection.id).label('count')
                )
                .where(Detection.timestamp >= yesterday)
                .group_by(func.extract('hour', Detection.timestamp))
                .order_by(func.count(Detection.id).desc())
                .limit(1)
            )
            peak_row = peak_hour_result.first()
            if peak_row:
                hour = int(peak_row.hour)
                peak_hour = f"{hour:02d}:00"
        except Exception:
            peak_hour = "N/A"
        
        # Calculate weekly change percentage
        weekly_change_percent = 0.0
        try:
            last_week_start = datetime.utcnow() - timedelta(days=7)
            prev_week_start = datetime.utcnow() - timedelta(days=14)
            
            # This week's detections
            this_week_result = await self.db.execute(
                select(func.count(Detection.id))
                .where(Detection.timestamp >= last_week_start)
            )
            this_week_count = this_week_result.scalar() or 0
            
            # Previous week's detections
            prev_week_result = await self.db.execute(
                select(func.count(Detection.id))
                .where(Detection.timestamp >= prev_week_start)
                .where(Detection.timestamp < last_week_start)
            )
            prev_week_count = prev_week_result.scalar() or 0
            
            if prev_week_count > 0:
                weekly_change_percent = ((this_week_count - prev_week_count) / prev_week_count) * 100
        except Exception:
            weekly_change_percent = 0.0
        
        return {
            "total_cameras": total_cameras,
            "active_cameras": active_cameras,
            "detections_24h": detections_24h,
            "total_detections": total_detections,
            "watchlist_persons": watchlist_count,
            "unverified_detections": unverified_count,
            "high_priority_alerts": high_priority,
            "peak_hour": peak_hour,
            "weekly_change_percent": round(weekly_change_percent, 1),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_detection_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        Get detection trends over time with accuracy metrics
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Detections by day with average confidence (accuracy)
        daily_result = await self.db.execute(
            select(
                func.date(Detection.timestamp).label('date'),
                func.count(Detection.id).label('count'),
                func.avg(Detection.confidence).label('avg_accuracy')
            )
            .where(Detection.timestamp >= start_date)
            .group_by(func.date(Detection.timestamp))
            .order_by(func.date(Detection.timestamp))
        )
        
        daily_data_raw = [
            {
                "date": row.date.isoformat(),
                "count": row.count,
                "accuracy": round(float(row.avg_accuracy or 0) * 100, 1)  # Convert to percentage
            }
            for row in daily_result.all()
        ]
        
        # Fill missing dates with zeros for complete graph
        all_dates = []
        for i in range(days):
            date = (datetime.utcnow() - timedelta(days=days-i-1)).date()
            all_dates.append(date)
        
        daily_data = []
        for date in all_dates:
            date_str = date.isoformat()
            existing = next((d for d in daily_data_raw if d['date'] == date_str), None)
            if existing:
                daily_data.append(existing)
            else:
                daily_data.append({
                    "date": date_str,
                    "count": 0,
                    "accuracy": 0
                })
        
        # Detections by type
        type_result = await self.db.execute(
            select(
                Detection.detection_type,
                func.count(Detection.id).label('count')
            )
            .where(Detection.timestamp >= start_date)
            .group_by(Detection.detection_type)
        )
        
        by_type = {
            row.detection_type: row.count
            for row in type_result.all()
        }
        
        return {
            "period_days": days,
            "daily_detections": daily_data,
            "by_type": by_type
        }
    
    async def get_camera_health(self) -> Dict[str, Any]:
        """
        Get health status of all cameras
        """
        result = await self.db.execute(select(Camera))
        cameras = result.scalars().all()
        
        health_data = []
        for camera in cameras:
            # Calculate uptime (mock calculation)
            uptime = 95.0 if camera.is_online else 0.0
            
            # Get recent detections count
            recent_detections_result = await self.db.execute(
                select(func.count(Detection.id))
                .where(Detection.camera_id == camera.id)
                .where(Detection.timestamp >= datetime.utcnow() - timedelta(hours=1))
            )
            recent_detections = recent_detections_result.scalar() or 0
            
            health_data.append({
                "camera_id": camera.id,
                "name": camera.name,
                "status": camera.health_status,
                "is_online": camera.is_online,
                "uptime_percentage": uptime,
                "recent_detections": recent_detections,
                "error_count": camera.error_count,
                "last_seen": camera.last_seen.isoformat() if camera.last_seen else None
            })
        
        return {"cameras": health_data}