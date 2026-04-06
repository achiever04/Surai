"""
Evidence management service for chain of custody
"""
import hashlib
from datetime import datetime
from typing import Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.evidence import Evidence
from app.models.detection import Detection

class EvidenceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage_path = Path("storage/local/evidence")
    
    async def create_evidence_record(
        self,
        detection_id: int,
        file_type: str,
        file_format: str,
        file_data: bytes,
        local_path: str,
        ipfs_cid: Optional[str] = None
    ) -> Evidence:
        """
        Create evidence record with chain of custody
        """
        # Generate evidence ID
        evidence_id = f"ev_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{detection_id}"
        
        # Compute hash
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Initialize chain of custody
        chain_of_custody = [
            {
                "action": "created",
                "actor": "system",
                "timestamp": datetime.utcnow().isoformat(),
                "location": "evidence_service"
            }
        ]
        
        # Create evidence record
        evidence = Evidence(
            evidence_id=evidence_id,
            detection_id=detection_id,
            file_type=file_type,
            file_format=file_format,
            file_size=len(file_data),
            file_hash=file_hash,
            local_path=local_path,
            ipfs_cid=ipfs_cid,
            chain_of_custody=chain_of_custody
        )
        
        self.db.add(evidence)
        await self.db.commit()
        await self.db.refresh(evidence)
        
        return evidence
    
    async def add_custody_event(
        self,
        evidence_id: int,
        action: str,
        actor: str
    ):
        """Add event to chain of custody"""
        result = await self.db.execute(
            select(Evidence).where(Evidence.id == evidence_id)
        )
        evidence = result.scalar_one_or_none()
        
        if evidence:
            custody_event = {
                "action": action,
                "actor": actor,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            evidence.chain_of_custody.append(custody_event)
            evidence.updated_at = datetime.utcnow()
            
            await self.db.commit()
    
    async def verify_integrity(self, evidence_id: int) -> bool:
        """
        Verify evidence integrity by comparing current hash with stored hash
        """
        result = await self.db.execute(
            select(Evidence).where(Evidence.id == evidence_id)
        )
        evidence = result.scalar_one_or_none()
        
        if not evidence:
            return False
        
        # Read file and compute current hash
        try:
            with open(evidence.local_path, "rb") as f:
                current_data = f.read()
            
            current_hash = hashlib.sha256(current_data).hexdigest()
            
            return current_hash == evidence.file_hash
        except Exception as e:
            print(f"Integrity verification failed: {e}")
            return False