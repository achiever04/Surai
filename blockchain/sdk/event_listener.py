"""
Blockchain event listener for real-time notifications
"""
import asyncio
from typing import Callable, Dict, Any, List
from loguru import logger
import json


class BlockchainEventListener:
    """Listen to blockchain events in real-time"""
    
    def __init__(self, fabric_client):
        """
        Initialize event listener
        
        Args:
            fabric_client: FabricClient instance
        """
        self.client = fabric_client
        self.listeners: Dict[str, List[Callable]] = {}
        self.is_running = False
    
    def register_listener(self, event_type: str, callback: Callable):
        """
        Register callback for specific event type
        
        Args:
            event_type: Type of event (e.g., 'EvidenceRegistered')
            callback: Async function to call when event occurs
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        
        self.listeners[event_type].append(callback)
        logger.info(f"Registered listener for event: {event_type}")
    
    def unregister_listener(self, event_type: str, callback: Callable):
        """Unregister callback for event type"""
        if event_type in self.listeners:
            self.listeners[event_type].remove(callback)
            logger.info(f"Unregistered listener for event: {event_type}")
    
    async def start_listening(
        self,
        channel_name: str,
        chaincode_name: str,
        event_filter: str = ".*"
    ):
        """
        Start listening to blockchain events
        
        Args:
            channel_name: Channel to listen to
            chaincode_name: Chaincode to monitor
            event_filter: Regex filter for event names
        """
        self.is_running = True
        logger.info(f"Started listening to events on {channel_name}/{chaincode_name}")
        
        try:
            # In production, use Fabric SDK's event hub
            # For now, implement polling mechanism
            while self.is_running:
                # Poll for events (placeholder for real event hub)
                await asyncio.sleep(5)
                
                # In real implementation:
                # events = await self.client.get_chaincode_events(
                #     channel_name, chaincode_name, event_filter
                # )
                # for event in events:
                #     await self._handle_event(event)
                
        except Exception as e:
            logger.error(f"Error in event listener: {e}")
        finally:
            self.is_running = False
    
    def stop_listening(self):
        """Stop listening to events"""
        self.is_running = False
        logger.info("Stopped listening to blockchain events")
    
    async def _handle_event(self, event: Dict[str, Any]):
        """
        Handle incoming blockchain event
        
        Args:
            event: Event data from blockchain
        """
        event_type = event.get("event_name")
        event_data = event.get("payload")
        
        logger.info(f"Received event: {event_type}")
        
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    await callback(event_data)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")
    
    async def wait_for_transaction(
        self,
        tx_id: str,
        timeout: int = 30
    ) -> bool:
        """
        Wait for specific transaction to be confirmed
        
        Args:
            tx_id: Transaction ID to wait for
            timeout: Timeout in seconds
            
        Returns:
            True if transaction confirmed, False if timeout
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            # Check transaction status
            try:
                # In production: query transaction status from blockchain
                # status = await self.client.query_transaction(tx_id)
                # if status == "VALID":
                #     return True
                
                # Placeholder: assume success after 2 seconds
                await asyncio.sleep(2)
                return True
                
            except Exception as e:
                logger.error(f"Error checking transaction: {e}")
            
            await asyncio.sleep(1)
        
        logger.warning(f"Transaction {tx_id} confirmation timeout")
        return False
    
    def create_event_callback(self, handler_func: Callable):
        """
        Decorator to create event callback
        
        Usage:
            @listener.create_event_callback
            async def on_evidence_registered(event_data):
                print(f"Evidence registered: {event_data}")
        """
        async def wrapper(event_data: Dict[str, Any]):
            try:
                await handler_func(event_data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
        
        return wrapper


class EventEmitter:
    """Emit custom blockchain events"""
    
    def __init__(self, fabric_client):
        self.client = fabric_client
    
    async def emit_event(
        self,
        channel_name: str,
        chaincode_name: str,
        event_name: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Emit custom event to blockchain
        
        Args:
            channel_name: Target channel
            chaincode_name: Target chaincode
            event_name: Event identifier
            event_data: Event payload
            
        Returns:
            True if event emitted successfully
        """
        try:
            # In production, chaincode emits events
            # This is a client-side placeholder
            logger.info(f"Emitting event: {event_name}")
            
            # Real implementation would invoke chaincode that emits event
            # result = await self.client.invoke_chaincode(
            #     channel_name=channel_name,
            #     chaincode_name=chaincode_name,
            #     function_name="EmitCustomEvent",
            #     args=[event_name, json.dumps(event_data)]
            # )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
            return False