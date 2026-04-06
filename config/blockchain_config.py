"""
Blockchain (Hyperledger Fabric) configuration
"""
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass
from config.settings import settings


@dataclass
class Organization:
    """Fabric organization configuration"""
    name: str
    msp_id: str
    peer_endpoints: List[str]
    ca_endpoint: str
    admin_user: str


@dataclass
class Channel:
    """Fabric channel configuration"""
    name: str
    orderer_endpoint: str
    participating_orgs: List[str]


class FabricNetworkConfig:
    """Hyperledger Fabric network configuration"""
    
    # Network paths
    NETWORK_PATH = Path(settings.FABRIC_NETWORK_PATH)
    CRYPTO_PATH = NETWORK_PATH / "organizations"
    CHANNEL_ARTIFACTS_PATH = NETWORK_PATH / "channel-artifacts"
    
    # Organizations
    ORGANIZATIONS = {
        "org1": Organization(
            name="Org1",
            msp_id=settings.FABRIC_ORG1_MSP,
            peer_endpoints=["peer0.org1.example.com:7051"],
            ca_endpoint="ca.org1.example.com:7054",
            admin_user="Admin@org1.example.com"
        ),
        "org2": Organization(
            name="Org2",
            msp_id=settings.FABRIC_ORG2_MSP,
            peer_endpoints=["peer0.org2.example.com:9051"],
            ca_endpoint="ca.org2.example.com:8054",
            admin_user="Admin@org2.example.com"
        )
    }
    
    # Channels
    CHANNELS = {
        "surveillance": Channel(
            name=settings.CHANNEL_NAME,
            orderer_endpoint="orderer.example.com:7050",
            participating_orgs=["org1", "org2"]
        )
    }
    
    # Chaincode configurations
    CHAINCODES = {
        "evidence": {
            "name": settings.EVIDENCE_CHAINCODE,
            "version": "1.0",
            "path": "github.com/chaincode/evidence-contract",
            "lang": "node"
        },
        "watchlist": {
            "name": settings.WATCHLIST_CHAINCODE,
            "version": "1.0",
            "path": "github.com/chaincode/watchlist-contract",
            "lang": "node"
        },
        "fl": {
            "name": "fl-contract",
            "version": "1.0",
            "path": "github.com/chaincode/fl-contract",
            "lang": "node"
        }
    }
    
    @classmethod
    def get_connection_profile(cls, org_name: str) -> Dict:
        """
        Generate Fabric connection profile for organization
        
        Args:
            org_name: Organization name (org1, org2)
            
        Returns:
            Connection profile dictionary
        """
        org = cls.ORGANIZATIONS[org_name]
        
        return {
            "name": f"{org.name}-network",
            "version": "1.0.0",
            "client": {
                "organization": org.name,
                "connection": {
                    "timeout": {
                        "peer": {"endorser": "300"},
                        "orderer": "300"
                    }
                }
            },
            "channels": {
                cls.CHANNELS["surveillance"].name: {
                    "orderers": ["orderer.example.com"],
                    "peers": {
                        peer: {
                            "endorsingPeer": True,
                            "chaincodeQuery": True,
                            "ledgerQuery": True,
                            "eventSource": True
                        } for peer in org.peer_endpoints
                    }
                }
            },
            "organizations": {
                org.name: {
                    "mspid": org.msp_id,
                    "peers": org.peer_endpoints,
                    "certificateAuthorities": [org.ca_endpoint]
                }
            },
            "orderers": {
                "orderer.example.com": {
                    "url": "grpc://orderer.example.com:7050"
                }
            },
            "peers": {
                peer: {
                    "url": f"grpc://{peer}"
                } for peer in org.peer_endpoints
            },
            "certificateAuthorities": {
                org.ca_endpoint: {
                    "url": f"http://{org.ca_endpoint}",
                    "caName": f"ca-{org_name}"
                }
            }
        }
    
    @classmethod
    def get_crypto_path(cls, org_name: str, component: str = "peers") -> Path:
        """
        Get path to crypto materials
        
        Args:
            org_name: Organization name
            component: Component type (peers, users, ca)
            
        Returns:
            Path to crypto materials
        """
        return cls.CRYPTO_PATH / org_name / component