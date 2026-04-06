"""
Utility functions for blockchain operations
"""
import hashlib
import json
from typing import Dict, Any, List
from datetime import datetime
import base64


def compute_transaction_hash(tx_data: Dict[str, Any]) -> str:
    """
    Compute hash of transaction data
    
    Args:
        tx_data: Transaction data dictionary
        
    Returns:
        SHA-256 hash as hex string
    """
    # Sort keys for consistent hashing
    json_str = json.dumps(tx_data, sort_keys=True)
    return hashlib.sha256(json_str.encode()).hexdigest()


def verify_transaction_signature(
    tx_data: Dict[str, Any],
    signature: str,
    public_key: str
) -> bool:
    """
    Verify transaction signature (placeholder)
    
    Args:
        tx_data: Transaction data
        signature: Digital signature
        public_key: Public key for verification
        
    Returns:
        True if signature valid
    """
    # In production, use cryptography library for real verification
    # from cryptography.hazmat.primitives import hashes
    # from cryptography.hazmat.primitives.asymmetric import padding
    
    # Placeholder implementation
    return len(signature) > 0 and len(public_key) > 0


def create_merkle_root(transactions: List[Dict[str, Any]]) -> str:
    """
    Create Merkle root hash from list of transactions
    
    Args:
        transactions: List of transaction dictionaries
        
    Returns:
        Merkle root hash
    """
    if not transactions:
        return hashlib.sha256(b"").hexdigest()
    
    # Compute hashes of all transactions
    hashes = [compute_transaction_hash(tx) for tx in transactions]
    
    # Build Merkle tree
    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])  # Duplicate last hash if odd number
        
        new_hashes = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            new_hash = hashlib.sha256(combined.encode()).hexdigest()
            new_hashes.append(new_hash)
        
        hashes = new_hashes
    
    return hashes[0]


def create_block_header(
    block_number: int,
    previous_hash: str,
    merkle_root: str,
    timestamp: datetime
) -> Dict[str, Any]:
    """
    Create blockchain block header
    
    Args:
        block_number: Block sequence number
        previous_hash: Hash of previous block
        merkle_root: Merkle root of transactions
        timestamp: Block creation time
        
    Returns:
        Block header dictionary
    """
    return {
        "block_number": block_number,
        "previous_hash": previous_hash,
        "merkle_root": merkle_root,
        "timestamp": timestamp.isoformat(),
        "version": 1
    }


def encode_chaincode_args(args: List[Any]) -> List[bytes]:
    """
    Encode arguments for chaincode invocation
    
    Args:
        args: List of arguments (strings, numbers, dicts)
        
    Returns:
        List of encoded arguments as bytes
    """
    encoded = []
    for arg in args:
        if isinstance(arg, str):
            encoded.append(arg.encode())
        elif isinstance(arg, (dict, list)):
            encoded.append(json.dumps(arg).encode())
        else:
            encoded.append(str(arg).encode())
    
    return encoded


def decode_chaincode_response(response: bytes) -> Any:
    """
    Decode chaincode response
    
    Args:
        response: Raw response bytes
        
    Returns:
        Decoded response (usually dict or string)
    """
    try:
        decoded = response.decode('utf-8')
        try:
            return json.loads(decoded)
        except json.JSONDecodeError:
            return decoded
    except UnicodeDecodeError:
        return response


def create_proposal_id() -> str:
    """
    Generate unique proposal ID for transactions
    
    Returns:
        Unique proposal ID
    """
    import uuid
    return str(uuid.uuid4())


def validate_transaction_format(tx: Dict[str, Any]) -> bool:
    """
    Validate transaction format
    
    Args:
        tx: Transaction dictionary
        
    Returns:
        True if format valid
    """
    required_fields = ["tx_id", "channel_name", "chaincode_name", "function_name"]
    return all(field in tx for field in required_fields)


def create_custody_event(
    actor: str,
    action: str,
    notes: str = ""
) -> Dict[str, Any]:
    """
    Create chain of custody event
    
    Args:
        actor: Person performing action
        action: Action performed
        notes: Optional notes
        
    Returns:
        Custody event dictionary
    """
    return {
        "actor": actor,
        "action": action,
        "notes": notes,
        "timestamp": datetime.utcnow().isoformat()
    }


def verify_evidence_chain(
    evidence_data: Dict[str, Any],
    custody_chain: List[Dict[str, Any]]
) -> bool:
    """
    Verify evidence chain of custody is valid
    
    Args:
        evidence_data: Original evidence data
        custody_chain: List of custody events
        
    Returns:
        True if chain is valid
    """
    if not custody_chain:
        return False
    
    # Verify chronological order
    timestamps = [
        datetime.fromisoformat(event["timestamp"])
        for event in custody_chain
    ]
    
    return timestamps == sorted(timestamps)


def format_blockchain_receipt(
    tx_id: str,
    tx_type: str,
    entity_id: str,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Format blockchain receipt for database storage
    
    Args:
        tx_id: Transaction ID
        tx_type: Type of transaction
        entity_id: Related entity ID
        payload: Transaction payload
        
    Returns:
        Formatted receipt dictionary
    """
    return {
        "tx_id": tx_id,
        "tx_type": tx_type,
        "entity_id": entity_id,
        "payload": payload,
        "created_at": datetime.utcnow().isoformat(),
        "status": "confirmed"
    }


def extract_transaction_metadata(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract metadata from transaction
    
    Args:
        tx: Transaction dictionary
        
    Returns:
        Metadata dictionary
    """
    return {
        "tx_id": tx.get("tx_id"),
        "timestamp": tx.get("timestamp"),
        "creator": tx.get("creator"),
        "channel": tx.get("channel_name")
    }


def serialize_for_blockchain(data: Dict[str, Any]) -> str:
    """
    Serialize data for blockchain storage
    
    Args:
        data: Data dictionary
        
    Returns:
        Serialized JSON string
    """
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def deserialize_from_blockchain(data: str) -> Dict[str, Any]:
    """
    Deserialize data from blockchain
    
    Args:
        data: Serialized JSON string
        
    Returns:
        Deserialized dictionary
    """
    return json.loads(data)