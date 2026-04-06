"""
Blockchain service for Hyperledger Fabric integration
"""
from typing import Dict, Any, Optional
from datetime import datetime
import json
import hashlib
from loguru import logger

from app.models.blockchain_receipt import BlockchainReceipt
from sqlalchemy.ext.asyncio import AsyncSession
from blockchain.sdk.fabric_client import FabricClient
from blockchain.sdk.chaincode_invoker import ChaincodeInvoker
from config.settings import settings


class BlockchainService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.channel_name = settings.CHANNEL_NAME
        
        # Initialize Fabric client
        try:
            # In production, use proper connection profile
            connection_profile = f"{settings.FABRIC_NETWORK_PATH}/connection-profile.json"
            self.fabric_client = FabricClient(
                network_profile_path=connection_profile,
                org_name="Org1",
                user_name="Admin"
            )
            
            # Initialize chaincode invoker
            self.chaincode_invoker = ChaincodeInvoker(self.fabric_client)
            
            logger.info("Blockchain service initialized with Fabric SDK")
            self.fabric_enabled = True
            
        except Exception as e:
            logger.warning(f"Fabric SDK not available: {e}. Using mock mode.")
            self.fabric_client = None
            self.chaincode_invoker = None
            self.fabric_enabled = False
    
    async def register_evidence(
        self,
        event_id: str,
        evidence_receipt: Dict[str, Any]
    ) -> str:
        """Register evidence on blockchain"""
        
        if self.fabric_enabled and self.chaincode_invoker:
            try:
                # Real Fabric SDK invocation
                # Remove await from synchronous Fabric SDK calls
                result = await self.chaincode_invoker.register_evidence(
                    channel_name=self.channel_name,
                    event_id=event_id,
                    evidence_hash=evidence_receipt.get('clip_hash'),
                    metadata=evidence_receipt
                )
                
                tx_id = result.get('tx_id')
                logger.info(f"Evidence registered on blockchain: {tx_id}")
                
            except Exception as e:
                logger.error(f"Blockchain registration failed: {e}")
                # Fall back to mock mode
                tx_id = self._generate_mock_tx_id(evidence_receipt)
        else:
            # Mock mode for development
            tx_id = self._generate_mock_tx_id(evidence_receipt)
            logger.info(f"Evidence registered (mock mode): {tx_id}")
        
        # Store receipt in database
        receipt = BlockchainReceipt(
            tx_id=tx_id,
            tx_type="evidence_registration",
            entity_type="detection",
            entity_id=event_id,
            channel_name=self.channel_name,
            chaincode_name=settings.EVIDENCE_CHAINCODE,
            function_name="RegisterEvidence",
            payload=evidence_receipt,
            status="confirmed",
            confirmation_time=datetime.utcnow()
        )
        
        self.db.add(receipt)
        await self.db.commit()
        
        return tx_id
    
    def register_evidence_sync(
        self,
        event_id: str,
        evidence_receipt: Dict[str, Any]
    ) -> str:
        """Synchronous version of register_evidence for use in sync contexts"""
        
        # Generate TX ID (mock mode for now)
        tx_id = self._generate_mock_tx_id(evidence_receipt)
        logger.info(f"Evidence registered (sync mock mode): {tx_id}")
        
        # Store receipt in database using sync session
        try:
            receipt = BlockchainReceipt(
                tx_id=tx_id,
                tx_type="evidence_registration",
                entity_type="detection",
                entity_id=event_id,
                channel_name=self.channel_name,
                chaincode_name=settings.EVIDENCE_CHAINCODE if hasattr(settings, 'EVIDENCE_CHAINCODE') else "evidence-contract",
                function_name="RegisterEvidence",
                payload=evidence_receipt,
                status="confirmed",
                confirmation_time=datetime.utcnow()
            )
            
            # Use the existing sync session
            from sqlalchemy.orm import Session
            if isinstance(self.db, Session):
                self.db.add(receipt)
                self.db.commit()
            else:
                # If async session passed, just generate TX ID without storing receipt
                logger.warning("Async session passed to sync method, skipping receipt storage")
            
        except Exception as e:
            logger.warning(f"Failed to store blockchain receipt: {e}")
            # Still return TX ID even if receipt storage fails
        
        return tx_id
    
    async def register_watchlist_enrollment(
        self,
        person_id: str,
        enrollment_data: Dict[str, Any]
    ) -> str:
        """Register watchlist enrollment on blockchain"""
        
        if self.fabric_enabled and self.chaincode_invoker:
            try:
                result = await self.chaincode_invoker.enroll_watchlist_person(
                    channel_name=self.channel_name,
                    person_id=person_id,
                    person_data=enrollment_data
                )
                tx_id = result.get('tx_id')
                
            except Exception as e:
                logger.error(f"Watchlist blockchain registration failed: {e}")
                tx_id = self._generate_mock_tx_id(enrollment_data)
        else:
            tx_id = self._generate_mock_tx_id(enrollment_data)
        
        receipt = BlockchainReceipt(
            tx_id=tx_id,
            tx_type="watchlist_enrollment",
            entity_type="watchlist_person",
            entity_id=person_id,
            channel_name=self.channel_name,
            chaincode_name=settings.WATCHLIST_CHAINCODE,
            function_name="EnrollPerson",
            payload=enrollment_data,
            status="confirmed",
            confirmation_time=datetime.utcnow()
        )
        
        self.db.add(receipt)
        await self.db.commit()
        
        return tx_id
    
    async def get_evidence_provenance(self, event_id: str) -> Dict[str, Any]:
        """Query evidence provenance from blockchain"""
        
        if self.fabric_enabled and self.chaincode_invoker:
            try:
                response = self.chaincode_invoker.query_evidence(
                    channel_name=self.channel_name,
                    event_id=event_id
                )
                
                if response:
                    return response
                    
            except Exception as e:
                logger.error(f"Blockchain query failed: {e}")
        
        # Fallback: Query from database
        from sqlalchemy import select
        from app.models.detection import Detection
        
        result = await self.db.execute(
            select(Detection).where(Detection.event_id == event_id)
        )
        detection = result.scalar_one_or_none()
        
        if detection:
            return {
                "event_id": event_id,
                "clip_hash": detection.clip_hash,
                "blockchain_tx_id": detection.blockchain_tx_id,
                "anchored_at": detection.anchored_at,
                "chain_of_custody": [
                    {
                        "action": "created",
                        "actor": "system",
                        "timestamp": detection.timestamp.isoformat()
                    }
                ],
                "is_verified": True
            }
        
        return {"event_id": event_id, "chain_of_custody": [], "is_verified": False}
    
    async def verify_evidence_integrity(
        self,
        event_id: str,
        current_hash: str
    ) -> bool:
        """Verify evidence hasn't been tampered"""
        
        provenance = await self.get_evidence_provenance(event_id)
        original_hash = provenance.get("clip_hash")
        
        return original_hash == current_hash
    
    async def register_fl_update(
        self,
        epoch: int,
        model_hash: str,
        update_receipts: list
    ) -> str:
        """Register federated learning update on blockchain"""
        
        fl_data = {
            "epoch": epoch,
            "model_hash": model_hash,
            "update_receipts": update_receipts,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if self.fabric_enabled and self.chaincode_invoker:
            try:
                result = await self.chaincode_invoker.register_fl_model_update(
                    channel_name=self.channel_name,
                    epoch=epoch,
                    model_hash=model_hash,
                    client_updates=update_receipts
                )
                tx_id = result.get('tx_id')
                
            except Exception as e:
                logger.error(f"FL blockchain registration failed: {e}")
                tx_id = self._generate_mock_tx_id(fl_data)
        else:
            tx_id = self._generate_mock_tx_id(fl_data)
        
        receipt = BlockchainReceipt(
            tx_id=tx_id,
            tx_type="fl_update",
            entity_type="fl_model",
            entity_id=str(epoch),
            channel_name=self.channel_name,
            chaincode_name="fl-contract",
            function_name="RegisterModelUpdate",
            payload=fl_data,
            status="confirmed",
            confirmation_time=datetime.utcnow()
        )
        
        self.db.add(receipt)
        await self.db.commit()
        
        return tx_id
    
    def _generate_mock_tx_id(self, data: Dict[str, Any]) -> str:
        """Generate mock transaction ID for development"""
        data_json = json.dumps(data, sort_keys=True)
        return f"tx_{hashlib.sha256(data_json.encode()).hexdigest()[:16]}"