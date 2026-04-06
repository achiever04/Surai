"""
IPFS client for decentralized file storage
"""
import ipfshttpclient
from typing import Optional
from pathlib import Path
from loguru import logger
from config.settings import settings
from storage.ipfs.ipfs_manager import IPFSStorageManager

class IPFSClient:
    """Client for interacting with IPFS"""
    
    def __init__(self, api_url: Optional[str] = None):
        """
        Initialize IPFS client
        
        Args:
            api_url: IPFS API URL or multiaddr (default from settings)
        """
        raw_url = api_url or settings.IPFS_API
        self.api_url = self._to_multiaddr(raw_url)
        self.client = None
        self._connect()
    
    @staticmethod
    def _to_multiaddr(url: str) -> str:
        """Convert HTTP URL to multiaddr format for ipfshttpclient.
        
        ipfshttpclient requires multiaddr format: /dns/host/tcp/port/http
        but users typically configure HTTP URLs: http://localhost:5001
        
        If the input is already multiaddr (starts with '/'), return as-is.
        """
        if url.startswith('/'):
            return url  # Already multiaddr format
        
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = parsed.hostname or 'localhost'
        port = parsed.port or 5001
        return f"/dns/{host}/tcp/{port}/http"
    
    def _connect(self):
        """Connect to IPFS node"""
        try:
            import warnings
            # Suppress VersionMismatch warning — Kubo v0.24.0 works fine
            # but ipfshttpclient only officially supports 0.5.0–0.9.0
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message="Unsupported daemon version")
                self.client = ipfshttpclient.connect(self.api_url)
            logger.info(f"Connected to IPFS at {self.api_url}")
        except Exception as e:
            # Changed from ERROR to WARNING - not critical
            logger.warning(f"IPFS not available ({e}). Using local storage only.")
            self.client = None
    
    @property
    def available(self) -> bool:
        """Check if IPFS client is connected and available."""
        return self.client is not None

    
    async def add_file(self, data: bytes, filename: Optional[str] = None) -> Optional[str]:
        """
        Add file to IPFS
        
        Args:
            data: File data as bytes
            filename: Optional filename
            
        Returns:
            IPFS CID or None if failed
        """
        if not self.client:
            logger.warning("IPFS client not connected")
            return None
        
        try:
            result = self.client.add_bytes(data)
            cid = result
            logger.info(f"File added to IPFS: {cid}")
            return cid
        except Exception as e:
            logger.error(f"Failed to add file to IPFS: {e}")
            return None
    
    async def add_file_from_path(self, file_path: str) -> Optional[str]:
        """
        Add file from local path to IPFS
        
        Args:
            file_path: Path to file
            
        Returns:
            IPFS CID or None
        """
        if not self.client:
            return None
        
        try:
            result = self.client.add(file_path)
            cid = result['Hash']
            logger.info(f"File {file_path} added to IPFS: {cid}")
            return cid
        except Exception as e:
            logger.error(f"Failed to add file from path: {e}")
            return None
    
    async def get_file(self, cid: str, output_path: Optional[str] = None) -> Optional[bytes]:
        """
        Get file from IPFS
        
        Args:
            cid: IPFS CID
            output_path: Optional path to save file
            
        Returns:
            File data as bytes or None
        """
        if not self.client:
            return None
        
        try:
            data = self.client.cat(cid)
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(data)
            
            return data
        except Exception as e:
            logger.error(f"Failed to get file from IPFS: {e}")
            return None
    
    def pin_file(self, cid: str) -> bool:
        """
        Pin file to prevent garbage collection
        
        Args:
            cid: IPFS CID
            
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.pin.add(cid)
            logger.info(f"File pinned: {cid}")
            return True
        except Exception as e:
            logger.error(f"Failed to pin file: {e}")
            return False
    
    def unpin_file(self, cid: str) -> bool:
        """
        Unpin file
        
        Args:
            cid: IPFS CID
            
        Returns:
            True if successful
        """
        if not self.client:
            return False
        
        try:
            self.client.pin.rm(cid)
            logger.info(f"File unpinned: {cid}")
            return True
        except Exception as e:
            logger.error(f"Failed to unpin file: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Check if connected to IPFS"""
        if not self.client:
            return False
        
        try:
            self.client.version()
            return True
        except:
            return False
    
    def upload_bytes_sync(self, data: bytes) -> Optional[str]:
        """Upload raw bytes to IPFS (sync version for background threads).
        
        Used by detection_processor._handle_detection_sync() which runs
        in a ThreadPoolExecutor — NOT an async context.
        
        Returns:
            IPFS CID string, or None if IPFS is unavailable
        """
        if not self.client:
            return None
        
        try:
            cid = self.client.add_bytes(data)
            logger.info(f"IPFS upload: {len(data)} bytes → {cid}")
            return cid
        except Exception as e:
            logger.warning(f"IPFS upload failed (using local only): {e}")
            return None
    
    def upload_file_sync(self, file_path: str) -> Optional[str]:
        """Upload file from local path to IPFS (sync version).
        
        Returns:
            IPFS CID string, or None if IPFS is unavailable
        """
        if not self.client:
            return None
        
        try:
            result = self.client.add(file_path)
            cid = result['Hash']
            logger.info(f"IPFS upload: {file_path} → {cid}")
            return cid
        except Exception as e:
            logger.warning(f"IPFS file upload failed (using local only): {e}")
            return None


# Module-level singleton — import as:
#   from app.utils.ipfs_client import ipfs_client
ipfs_client = IPFSClient()