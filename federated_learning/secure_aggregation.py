"""
Secure aggregation protocols for privacy-preserving federated learning
"""
import torch
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import OrderedDict
import hashlib
import secrets
from loguru import logger


class SecureMaskGenerator:
    """Generate secure random masks for model encryption"""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize mask generator
        
        Args:
            seed: Random seed for reproducibility
        """
        self.seed = seed
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
    
    def generate_mask(self, shape: tuple) -> torch.Tensor:
        """
        Generate random mask with same shape as model parameter
        
        Args:
            shape: Shape of parameter tensor
            
        Returns:
            Random mask tensor
        """
        return torch.randn(shape)
    
    def generate_model_mask(self, model: OrderedDict) -> OrderedDict:
        """
        Generate mask for entire model
        
        Args:
            model: Model state dict
            
        Returns:
            Mask state dict with same structure
        """
        mask = OrderedDict()
        
        for key, param in model.items():
            mask[key] = self.generate_mask(param.shape)
        
        return mask


class SecureAggregationProtocol:
    """Implement secure aggregation protocol for federated learning"""
    
    def __init__(self):
        self.client_masks: Dict[int, OrderedDict] = {}
        self.shared_secrets: Dict[Tuple[int, int], bytes] = {}
    
    def setup_client(self, client_id: int, model_template: OrderedDict):
        """
        Setup secure aggregation for client
        
        Args:
            client_id: Client identifier
            model_template: Template model for mask generation
        """
        mask_generator = SecureMaskGenerator()
        self.client_masks[client_id] = mask_generator.generate_model_mask(model_template)
        
        logger.info(f"Setup secure aggregation for client {client_id}")
    
    def generate_pairwise_secret(self, client_i: int, client_j: int) -> bytes:
        """
        Generate shared secret between two clients
        
        Args:
            client_i: First client ID
            client_j: Second client ID
            
        Returns:
            Shared secret bytes
        """
        # In production, use Diffie-Hellman key exchange
        # For demo, generate deterministic secret
        key = tuple(sorted([client_i, client_j]))
        
        if key not in self.shared_secrets:
            secret = secrets.token_bytes(32)
            self.shared_secrets[key] = secret
        
        return self.shared_secrets[key]
    
    def mask_model(
        self,
        client_id: int,
        model: OrderedDict,
        peer_clients: List[int]
    ) -> OrderedDict:
        """
        Mask model with pairwise secrets before sending to server
        
        Args:
            client_id: This client's ID
            model: Client's trained model
            peer_clients: List of other client IDs
            
        Returns:
            Masked model
        """
        masked_model = OrderedDict()
        
        for key, param in model.items():
            masked_param = param.clone()
            
            # Add masks from pairwise secrets
            for peer_id in peer_clients:
                if peer_id == client_id:
                    continue
                
                # Get shared secret
                secret = self.generate_pairwise_secret(client_id, peer_id)
                
                # Generate mask from secret
                mask = self._secret_to_mask(secret, param.shape)
                
                # Add or subtract based on client ordering
                if client_id < peer_id:
                    masked_param += mask
                else:
                    masked_param -= mask
            
            masked_model[key] = masked_param
        
        return masked_model
    
    def unmask_aggregated_model(
        self,
        aggregated_model: OrderedDict,
        active_clients: List[int]
    ) -> OrderedDict:
        """
        Remove masks from aggregated model (done by server)
        
        Args:
            aggregated_model: Sum of masked client models
            active_clients: List of clients who participated
            
        Returns:
            Unmasked aggregated model
        """
        # In secure aggregation, pairwise masks cancel out
        # when summing all clients' masked models
        # No unmasking needed if all clients participated
        
        # If some clients dropped out, need to compensate
        # (simplified implementation)
        
        return aggregated_model
    
    def _secret_to_mask(self, secret: bytes, shape: tuple) -> torch.Tensor:
        """
        Convert shared secret to deterministic mask
        
        Args:
            secret: Shared secret bytes
            shape: Shape of mask tensor
            
        Returns:
            Mask tensor
        """
        # Use secret as seed for mask generation
        seed = int.from_bytes(secret[:8], 'big')
        generator = torch.Generator().manual_seed(seed)
        
        mask = torch.randn(shape, generator=generator)
        return mask
    
    def verify_client_contribution(
        self,
        client_id: int,
        masked_model: OrderedDict,
        commitment_hash: str
    ) -> bool:
        """
        Verify client's contribution using commitment
        
        Args:
            client_id: Client identifier
            masked_model: Client's masked model
            commitment_hash: Hash commitment from client
            
        Returns:
            True if verification passes
        """
        # Compute hash of masked model
        computed_hash = self._compute_model_hash(masked_model)
        
        return computed_hash == commitment_hash
    
    def _compute_model_hash(self, model: OrderedDict) -> str:
        """Compute hash of model for verification"""
        hasher = hashlib.sha256()
        
        for key in sorted(model.keys()):
            param = model[key]
            hasher.update(param.cpu().numpy().tobytes())
        
        return hasher.hexdigest()


class DifferentialPrivacy:
    """Add differential privacy to federated learning"""
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Initialize DP mechanism
        
        Args:
            epsilon: Privacy budget (smaller = more privacy)
            delta: Privacy loss probability
        """
        self.epsilon = epsilon
        self.delta = delta
    
    def add_noise_to_gradients(
        self,
        gradients: OrderedDict,
        clip_norm: float = 1.0
    ) -> OrderedDict:
        """
        Add calibrated noise to gradients for DP
        
        Args:
            gradients: Gradient state dict
            clip_norm: Clipping threshold
            
        Returns:
            Noisy gradients
        """
        # Clip gradients
        clipped_grads = self._clip_gradients(gradients, clip_norm)
        
        # Compute noise scale using Gaussian mechanism
        noise_scale = self._compute_noise_scale(clip_norm)
        
        # Add noise
        noisy_grads = OrderedDict()
        for key, grad in clipped_grads.items():
            noise = torch.randn_like(grad) * noise_scale
            noisy_grads[key] = grad + noise
        
        logger.info(f"Added DP noise (epsilon={self.epsilon}, scale={noise_scale:.4f})")
        return noisy_grads
    
    def _clip_gradients(
        self,
        gradients: OrderedDict,
        clip_norm: float
    ) -> OrderedDict:
        """Clip gradients to bound sensitivity"""
        # Compute total norm
        total_norm = 0.0
        for grad in gradients.values():
            total_norm += torch.norm(grad).item() ** 2
        total_norm = np.sqrt(total_norm)
        
        # Clip if necessary
        clip_factor = min(1.0, clip_norm / (total_norm + 1e-6))
        
        clipped = OrderedDict()
        for key, grad in gradients.items():
            clipped[key] = grad * clip_factor
        
        return clipped
    
    def _compute_noise_scale(self, sensitivity: float) -> float:
        """
        Compute noise scale for Gaussian mechanism
        
        Args:
            sensitivity: L2 sensitivity (clip norm)
            
        Returns:
            Noise standard deviation
        """
        # Gaussian mechanism: σ = sensitivity * sqrt(2 * ln(1.25/delta)) / epsilon
        noise_scale = sensitivity * np.sqrt(2 * np.log(1.25 / self.delta)) / self.epsilon
        return noise_scale
    
    def compute_privacy_spent(self, num_rounds: int) -> Tuple[float, float]:
        """
        Compute total privacy spent after multiple rounds
        
        Args:
            num_rounds: Number of training rounds
            
        Returns:
            (total_epsilon, total_delta)
        """
        # Basic composition (can be improved with advanced composition)
        total_epsilon = self.epsilon * np.sqrt(num_rounds)
        total_delta = self.delta * num_rounds
        
        return total_epsilon, total_delta


class HomomorphicEncryption:
    """Simplified homomorphic encryption for secure aggregation"""
    
    def __init__(self, key_size: int = 2048):
        """
        Initialize HE scheme
        
        Args:
            key_size: Encryption key size in bits
        """
        self.key_size = key_size
        self.public_key = None
        self.private_key = None
        
        # In production, use actual HE library (PySEAL, TenSEAL)
        logger.warning("Using simplified HE - not cryptographically secure")
    
    def generate_keys(self):
        """Generate public/private key pair"""
        # Placeholder: In production, use real HE key generation
        self.public_key = secrets.token_bytes(self.key_size // 8)
        self.private_key = secrets.token_bytes(self.key_size // 8)
        
        logger.info("Generated HE keys")
    
    def encrypt_model(
        self,
        model: OrderedDict,
        public_key: bytes
    ) -> OrderedDict:
        """
        Encrypt model with public key
        
        Args:
            model: Model state dict
            public_key: Public encryption key
            
        Returns:
            Encrypted model
        """
        # Placeholder: In production, use real HE encryption
        encrypted = OrderedDict()
        
        for key, param in model.items():
            # Simple XOR encryption (NOT SECURE - for demo only)
            encrypted[key] = param + 0.001  # Add small noise
        
        return encrypted
    
    def decrypt_model(
        self,
        encrypted_model: OrderedDict,
        private_key: bytes
    ) -> OrderedDict:
        """
        Decrypt model with private key
        
        Args:
            encrypted_model: Encrypted model
            private_key: Private decryption key
            
        Returns:
            Decrypted model
        """
        # Placeholder: In production, use real HE decryption
        decrypted = OrderedDict()
        
        for key, param in encrypted_model.items():
            decrypted[key] = param - 0.001  # Remove noise
        
        return decrypted
    
    def aggregate_encrypted(
        self,
        encrypted_models: List[OrderedDict]
    ) -> OrderedDict:
        """
        Aggregate encrypted models (homomorphic property)
        
        Args:
            encrypted_models: List of encrypted models
            
        Returns:
            Aggregated encrypted model
        """
        if not encrypted_models:
            return OrderedDict()
        
        aggregated = OrderedDict()
        
        for key in encrypted_models[0].keys():
            # Sum encrypted values (works with additive HE)
            aggregated[key] = sum(
                model[key] for model in encrypted_models
            ) / len(encrypted_models)
        
        return aggregated