"""
Chaincode invocation wrapper for easy smart contract calls
"""
from typing import Dict, Any, List, Optional
import json
from loguru import logger


class ChaincodeInvoker:
    """High-level wrapper for chaincode invocations"""
    
    def __init__(self, fabric_client):
        """
        Initialize chaincode invoker
        
        Args:
            fabric_client: FabricClient instance
        """
        self.client = fabric_client
    
    async def register_evidence(
        self,
        channel_name: str,
        event_id: str,
        evidence_hash: str,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Register evidence on blockchain
        
        Args:
            channel_name: Blockchain channel name
            event_id: Unique event identifier
            evidence_hash: SHA-256 hash of evidence
            metadata: Additional evidence metadata
            
        Returns:
            Transaction result with tx_id
        """
        try:
            args = [
                event_id,
                evidence_hash,
                json.dumps(metadata)
            ]
            
            result = await self.client.invoke_chaincode(
                channel_name=channel_name,
                chaincode_name="evidence-contract",
                function_name="RegisterEvidence",
                args=args
            )
            
            logger.info(f"Evidence registered: {event_id}, tx_id: {result.get('tx_id')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to register evidence: {e}")
            return {"success": False, "error": str(e)}
    
    async def query_evidence(
        self,
        channel_name: str,
        event_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Query evidence from blockchain
        
        Args:
            channel_name: Blockchain channel name
            event_id: Event identifier
            
        Returns:
            Evidence data or None
        """
        try:
            args = [event_id]
            
            result = await self.client.query_chaincode(
                channel_name=channel_name,
                chaincode_name="evidence-contract",
                function_name="QueryEvidence",
                args=args
            )
            
            if result.get("success"):
                return result.get("data")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to query evidence: {e}")
            return None
    
    async def update_custody(
        self,
        channel_name: str,
        event_id: str,
        actor: str,
        action: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update chain of custody for evidence
        
        Args:
            channel_name: Blockchain channel name
            event_id: Event identifier
            actor: Person performing action
            action: Action performed (viewed, exported, etc.)
            notes: Optional notes
            
        Returns:
            Transaction result
        """
        try:
            custody_event = {
                "actor": actor,
                "action": action,
                "notes": notes or "",
                "timestamp": json.dumps({"$date": None})  # Will be set by chaincode
            }
            
            args = [
                event_id,
                json.dumps(custody_event)
            ]
            
            result = await self.client.invoke_chaincode(
                channel_name=channel_name,
                chaincode_name="evidence-contract",
                function_name="UpdateCustody",
                args=args
            )
            
            logger.info(f"Custody updated: {event_id}, action: {action}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to update custody: {e}")
            return {"success": False, "error": str(e)}
    
    async def enroll_watchlist_person(
        self,
        channel_name: str,
        person_id: str,
        person_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enroll person in watchlist on blockchain
        
        Args:
            channel_name: Blockchain channel name
            person_id: Unique person identifier
            person_data: Person enrollment data
            
        Returns:
            Transaction result
        """
        try:
            args = [
                person_id,
                json.dumps(person_data)
            ]
            
            result = await self.client.invoke_chaincode(
                channel_name=channel_name,
                chaincode_name="watchlist-contract",
                function_name="EnrollPerson",
                args=args
            )
            
            logger.info(f"Watchlist person enrolled: {person_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to enroll person: {e}")
            return {"success": False, "error": str(e)}
    
    async def query_watchlist_person(
        self,
        channel_name: str,
        person_id: str
    ) -> Optional[Dict[str, Any]]:
        """Query watchlist person from blockchain"""
        try:
            args = [person_id]
            
            result = await self.client.query_chaincode(
                channel_name=channel_name,
                chaincode_name="watchlist-contract",
                function_name="QueryPerson",
                args=args
            )
            
            if result.get("success"):
                return result.get("data")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to query person: {e}")
            return None
    
    async def register_fl_model_update(
        self,
        channel_name: str,
        epoch: int,
        model_hash: str,
        client_updates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Register federated learning model update
        
        Args:
            channel_name: Blockchain channel name
            epoch: Training epoch number
            model_hash: Hash of aggregated model
            client_updates: List of client update receipts
            
        Returns:
            Transaction result
        """
        try:
            update_data = {
                "epoch": epoch,
                "model_hash": model_hash,
                "client_updates": client_updates,
                "timestamp": json.dumps({"$date": None})
            }
            
            args = [
                str(epoch),
                json.dumps(update_data)
            ]
            
            result = await self.client.invoke_chaincode(
                channel_name=channel_name,
                chaincode_name="fl-contract",
                function_name="RegisterModelUpdate",
                args=args
            )
            
            logger.info(f"FL model update registered: epoch {epoch}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to register FL update: {e}")
            return {"success": False, "error": str(e)}
    
    async def query_fl_model(
        self,
        channel_name: str,
        epoch: int
    ) -> Optional[Dict[str, Any]]:
        """Query FL model update from blockchain"""
        try:
            args = [str(epoch)]
            
            result = await self.client.query_chaincode(
                channel_name=channel_name,
                chaincode_name="fl-contract",
                function_name="QueryModelUpdate",
                args=args
            )
            
            if result.get("success"):
                return result.get("data")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to query FL model: {e}")
            return None
    
    async def get_evidence_history(
        self,
        channel_name: str,
        event_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get complete history of evidence from blockchain
        
        Args:
            channel_name: Blockchain channel name
            event_id: Event identifier
            
        Returns:
            List of historical records
        """
        try:
            args = [event_id]
            
            result = await self.client.query_chaincode(
                channel_name=channel_name,
                chaincode_name="evidence-contract",
                function_name="GetEvidenceHistory",
                args=args
            )
            
            if result.get("success"):
                return result.get("data", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get evidence history: {e}")
            return []