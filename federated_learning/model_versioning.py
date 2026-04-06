"""
Model versioning and management for federated learning
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import OrderedDict
import torch
from loguru import logger


class ModelVersion:
    """Represents a specific model version"""
    
    def __init__(
        self,
        version: str,
        epoch: int,
        model_hash: str,
        model_path: str,
        metrics: Dict[str, float],
        metadata: Dict[str, Any]
    ):
        self.version = version
        self.epoch = epoch
        self.model_hash = model_hash
        self.model_path = model_path
        self.metrics = metrics
        self.metadata = metadata
        self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "version": self.version,
            "epoch": self.epoch,
            "model_hash": self.model_hash,
            "model_path": self.model_path,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ModelVersion':
        """Create from dictionary"""
        version = cls(
            version=data["version"],
            epoch=data["epoch"],
            model_hash=data["model_hash"],
            model_path=data["model_path"],
            metrics=data["metrics"],
            metadata=data["metadata"]
        )
        version.created_at = datetime.fromisoformat(data["created_at"])
        return version


class ModelVersionManager:
    """Manage model versions for federated learning"""
    
    def __init__(self, storage_dir: str = "storage/models/checkpoints"):
        """
        Initialize version manager
        
        Args:
            storage_dir: Directory to store model checkpoints
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.versions: Dict[str, ModelVersion] = {}
        self.version_history: List[str] = []
        
        # Load existing versions
        self._load_version_registry()
    
    def save_version(
        self,
        model: OrderedDict,
        epoch: int,
        metrics: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ModelVersion:
        """
        Save new model version
        
        Args:
            model: Model state dict
            epoch: Training epoch
            metrics: Performance metrics
            metadata: Additional metadata
            
        Returns:
            ModelVersion object
        """
        # Generate version string
        version = f"v{epoch}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Compute model hash
        model_hash = self._compute_model_hash(model)
        
        # Save model file
        model_filename = f"{version}.pth"
        model_path = self.storage_dir / model_filename
        torch.save(model, model_path)
        
        # Create version object
        model_version = ModelVersion(
            version=version,
            epoch=epoch,
            model_hash=model_hash,
            model_path=str(model_path),
            metrics=metrics,
            metadata=metadata or {}
        )
        
        # Store in registry
        self.versions[version] = model_version
        self.version_history.append(version)
        
        # Save registry
        self._save_version_registry()
        
        logger.info(f"Saved model version: {version} (epoch {epoch}, hash: {model_hash[:8]})")
        return model_version
    
    def load_version(self, version: str) -> Optional[OrderedDict]:
        """
        Load specific model version
        
        Args:
            version: Version string
            
        Returns:
            Model state dict or None
        """
        if version not in self.versions:
            logger.error(f"Version {version} not found")
            return None
        
        model_version = self.versions[version]
        
        try:
            model = torch.load(model_version.model_path, map_location='cpu')
            logger.info(f"Loaded model version: {version}")
            return model
        except Exception as e:
            logger.error(f"Failed to load model version {version}: {e}")
            return None
    
    def get_latest_version(self) -> Optional[ModelVersion]:
        """Get most recent model version"""
        if not self.version_history:
            return None
        
        latest_version_str = self.version_history[-1]
        return self.versions.get(latest_version_str)
    
    def get_version_info(self, version: str) -> Optional[ModelVersion]:
        """Get information about specific version"""
        return self.versions.get(version)
    
    def list_versions(self) -> List[ModelVersion]:
        """List all versions"""
        return [self.versions[v] for v in self.version_history]
    
    def compare_versions(
        self,
        version1: str,
        version2: str
    ) -> Dict[str, Any]:
        """
        Compare two model versions
        
        Args:
            version1: First version
            version2: Second version
            
        Returns:
            Comparison results
        """
        v1 = self.versions.get(version1)
        v2 = self.versions.get(version2)
        
        if not v1 or not v2:
            return {"error": "One or both versions not found"}
        
        comparison = {
            "version1": version1,
            "version2": version2,
            "epoch_diff": v2.epoch - v1.epoch,
            "metrics_diff": {},
            "same_hash": v1.model_hash == v2.model_hash
        }
        
        # Compare metrics
        common_metrics = set(v1.metrics.keys()) & set(v2.metrics.keys())
        for metric in common_metrics:
            comparison["metrics_diff"][metric] = v2.metrics[metric] - v1.metrics[metric]
        
        return comparison
    
    def rollback_to_version(self, version: str) -> bool:
        """
        Rollback to previous version (makes it the latest)
        
        Args:
            version: Version to rollback to
            
        Returns:
            True if successful
        """
        if version not in self.versions:
            logger.error(f"Version {version} not found")
            return False
        
        # Load the old version
        old_model = self.load_version(version)
        if old_model is None:
            return False
        
        # Save as new version with "rollback" metadata
        old_version_obj = self.versions[version]
        
        self.save_version(
            model=old_model,
            epoch=old_version_obj.epoch,
            metrics=old_version_obj.metrics,
            metadata={
                **old_version_obj.metadata,
                "rollback_from": version,
                "rollback_at": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Rolled back to version: {version}")
        return True
    
    def get_best_version(self, metric: str = "accuracy") -> Optional[ModelVersion]:
        """
        Get best version based on metric
        
        Args:
            metric: Metric to optimize (accuracy, loss, etc.)
            
        Returns:
            Best model version
        """
        if not self.versions:
            return None
        
        best_version = None
        best_value = float('-inf') if metric != "loss" else float('inf')
        
        for version in self.versions.values():
            if metric not in version.metrics:
                continue
            
            value = version.metrics[metric]
            
            if metric == "loss":
                if value < best_value:
                    best_value = value
                    best_version = version
            else:
                if value > best_value:
                    best_value = value
                    best_version = version
        
        return best_version
    
    def cleanup_old_versions(self, keep_last_n: int = 10):
        """
        Remove old model versions, keeping only last N
        
        Args:
            keep_last_n: Number of recent versions to keep
        """
        if len(self.version_history) <= keep_last_n:
            return
        
        versions_to_remove = self.version_history[:-keep_last_n]
        
        for version in versions_to_remove:
            model_version = self.versions[version]
            
            # Delete model file
            try:
                Path(model_version.model_path).unlink()
            except Exception as e:
                logger.warning(f"Failed to delete model file: {e}")
            
            # Remove from registry
            del self.versions[version]
        
        # Update history
        self.version_history = self.version_history[-keep_last_n:]
        
        # Save registry
        self._save_version_registry()
        
        logger.info(f"Cleaned up {len(versions_to_remove)} old versions")
    
    def _compute_model_hash(self, model: OrderedDict) -> str:
        """Compute SHA-256 hash of model parameters"""
        hasher = hashlib.sha256()
        
        for key in sorted(model.keys()):
            param = model[key]
            hasher.update(param.cpu().numpy().tobytes())
        
        return hasher.hexdigest()
    
    def _save_version_registry(self):
        """Save version registry to disk"""
        registry_path = self.storage_dir / "version_registry.json"
        
        registry_data = {
            "versions": {
                v: self.versions[v].to_dict()
                for v in self.versions
            },
            "version_history": self.version_history
        }
        
        with open(registry_path, 'w') as f:
            json.dump(registry_data, f, indent=2)
    
    def _load_version_registry(self):
        """Load version registry from disk"""
        registry_path = self.storage_dir / "version_registry.json"
        
        if not registry_path.exists():
            return
        
        try:
            with open(registry_path, 'r') as f:
                registry_data = json.load(f)
            
            self.versions = {
                v: ModelVersion.from_dict(data)
                for v, data in registry_data["versions"].items()
            }
            self.version_history = registry_data["version_history"]
            
            logger.info(f"Loaded {len(self.versions)} model versions")
        except Exception as e:
            logger.error(f"Failed to load version registry: {e}")
    
    def export_version_report(self, output_file: str):
        """Export version history report"""
        report = {
            "total_versions": len(self.versions),
            "versions": [v.to_dict() for v in self.list_versions()],
            "best_by_accuracy": self.get_best_version("accuracy").to_dict() if self.get_best_version("accuracy") else None,
            "best_by_loss": self.get_best_version("loss").to_dict() if self.get_best_version("loss") else None,
            "latest": self.get_latest_version().to_dict() if self.get_latest_version() else None
        }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Exported version report to {output_file}")