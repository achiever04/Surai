import grpc
from hfc.fabric import Client
from typing import Dict, Any
import json

class FabricClient:
    def __init__(self, network_profile_path: str, org_name: str, user_name: str):
        """
        Initialize Hyperledger Fabric client
        
        Args:
            network_profile_path: Path to connection profile JSON
            org_name: Organization name (Org1, Org2)
            user_name: User identity
        """
        self.client = Client(net_profile=network_profile_path)
        self.org_name = org_name
        self.user_name = user_name
        self.user = None
        
    async def initialize(self):
        """Load user credentials"""
        self.user = self.client.get_user(self.org_name, self.user_name)
        
    def invoke_chaincode(  # Remove async
        self,
        channel_name: str,
        chaincode_name: str,
        function_name: str,
        args: list
    ) -> Dict[str, Any]:
        """Invoke chaincode function (write operation)"""
        try:
            # Fabric SDK is synchronous, not async
            response = self.client.chaincode_invoke(
                requestor=self.user,
                channel_name=channel_name,
                peers=['peer0.org1.example.com'],
                args=args,
                cc_name=chaincode_name,
                fcn=function_name,
                wait_for_event=True
            )
            
            return {
                "success": True,
                "tx_id": response,
                "message": "Transaction committed successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def query_chaincode(
        self,
        channel_name: str,
        chaincode_name: str,
        function_name: str,
        args: list
    ) -> Dict[str, Any]:
        """
        Query chaincode (read operation)
        """
        try:
            response = await self.client.chaincode_query(
                requestor=self.user,
                channel_name=channel_name,
                peers=['peer0.org1.example.com'],
                args=args,
                cc_name=chaincode_name,
                fcn=function_name
            )
            
            return {
                "success": True,
                "data": json.loads(response)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }