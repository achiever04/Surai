"""
Face embedding extraction and management
"""
import numpy as np
from typing import List, Optional, Tuple
import pickle
from pathlib import Path
from loguru import logger


class FaceEmbeddingManager:
    """Manage face embeddings for recognition"""
    
    def __init__(self, embedding_dim: int = 512):
        """
        Initialize embedding manager
        
        Args:
            embedding_dim: Dimension of face embeddings
        """
        self.embedding_dim = embedding_dim
        self.embeddings = []
        self.labels = []
        self.metadata = []
    
    def add_embedding(
        self,
        embedding: np.ndarray,
        label: str,
        metadata: Optional[dict] = None
    ):
        """
        Add embedding to collection
        
        Args:
            embedding: Face embedding vector
            label: Person identifier
            metadata: Additional metadata
        """
        if embedding.shape[0] != self.embedding_dim:
            raise ValueError(f"Expected embedding dim {self.embedding_dim}, got {embedding.shape[0]}")
        
        self.embeddings.append(embedding)
        self.labels.append(label)
        self.metadata.append(metadata or {})
    
    def add_multiple_embeddings(
        self,
        embeddings: List[np.ndarray],
        label: str,
        metadata: Optional[dict] = None
    ):
        """Add multiple embeddings for same person"""
        for embedding in embeddings:
            self.add_embedding(embedding, label, metadata)
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 1,
        threshold: float = 0.4
    ) -> List[Tuple[str, float, dict]]:
        """
        Search for similar embeddings
        
        Args:
            query_embedding: Query embedding
            top_k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of (label, similarity, metadata) tuples
        """
        if not self.embeddings:
            return []
        
        # Calculate similarities (cosine similarity for normalized embeddings)
        embeddings_array = np.array(self.embeddings)
        similarities = np.dot(embeddings_array, query_embedding)
        
        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]
        
        # Filter by threshold
        results = []
        for idx in top_indices:
            similarity = float(similarities[idx])
            if similarity >= threshold:
                results.append((
                    self.labels[idx],
                    similarity,
                    self.metadata[idx]
                ))
        
        return results
    
    def get_embeddings_by_label(self, label: str) -> List[np.ndarray]:
        """Get all embeddings for a specific label"""
        return [
            emb for emb, lbl in zip(self.embeddings, self.labels)
            if lbl == label
        ]
    
    def remove_by_label(self, label: str) -> int:
        """
        Remove all embeddings for a label
        
        Returns:
            Number of embeddings removed
        """
        indices_to_remove = [
            i for i, lbl in enumerate(self.labels)
            if lbl == label
        ]
        
        # Remove in reverse order to maintain indices
        for idx in sorted(indices_to_remove, reverse=True):
            del self.embeddings[idx]
            del self.labels[idx]
            del self.metadata[idx]
        
        return len(indices_to_remove)
    
    def update_label(self, old_label: str, new_label: str):
        """Update label for all matching embeddings"""
        for i, label in enumerate(self.labels):
            if label == old_label:
                self.labels[i] = new_label
    
    def get_statistics(self) -> dict:
        """Get statistics about embeddings"""
        from collections import Counter
        
        label_counts = Counter(self.labels)
        
        return {
            "total_embeddings": len(self.embeddings),
            "unique_labels": len(label_counts),
            "embeddings_per_label": dict(label_counts),
            "embedding_dimension": self.embedding_dim
        }
    
    def compute_centroid(self, label: str) -> Optional[np.ndarray]:
        """Compute centroid embedding for a label"""
        embeddings = self.get_embeddings_by_label(label)
        
        if not embeddings:
            return None
        
        centroid = np.mean(embeddings, axis=0)
        # Normalize
        centroid = centroid / np.linalg.norm(centroid)
        
        return centroid
    
    def save(self, filepath: Path):
        """Save embeddings to file"""
        data = {
            "embeddings": self.embeddings,
            "labels": self.labels,
            "metadata": self.metadata,
            "embedding_dim": self.embedding_dim
        }
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump(data, f)
        
        logger.info(f"Saved {len(self.embeddings)} embeddings to {filepath}")
    
    def load(self, filepath: Path):
        """Load embeddings from file"""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        self.embeddings = data["embeddings"]
        self.labels = data["labels"]
        self.metadata = data["metadata"]
        self.embedding_dim = data["embedding_dim"]
        
        logger.info(f"Loaded {len(self.embeddings)} embeddings from {filepath}")
    
    def clear(self):
        """Clear all embeddings"""
        self.embeddings.clear()
        self.labels.clear()
        self.metadata.clear()


class EmbeddingClusterer:
    """Cluster face embeddings to find similar faces"""
    
    @staticmethod
    def cluster_embeddings(
        embeddings: List[np.ndarray],
        threshold: float = 0.5,
        min_cluster_size: int = 2
    ) -> List[List[int]]:
        """
        Cluster embeddings using similarity threshold
        
        Args:
            embeddings: List of embeddings
            threshold: Similarity threshold for clustering
            min_cluster_size: Minimum number of items in cluster
            
        Returns:
            List of clusters (each cluster is list of indices)
        """
        from sklearn.cluster import AgglomerativeClustering
        
        if len(embeddings) < min_cluster_size:
            return []
        
        # Convert to array
        X = np.array(embeddings)
        
        # Perform clustering
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1 - threshold,
            metric='cosine',
            linkage='average'
        )
        
        labels = clustering.fit_predict(X)
        
        # Group by cluster
        clusters = {}
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        # Filter by minimum size
        valid_clusters = [
            cluster for cluster in clusters.values()
            if len(cluster) >= min_cluster_size
        ]
        
        return valid_clusters
    
    @staticmethod
    def find_outliers(
        embeddings: List[np.ndarray],
        threshold: float = 0.3
    ) -> List[int]:
        """
        Find outlier embeddings that don't match any others
        
        Returns:
            List of outlier indices
        """
        n = len(embeddings)
        if n < 2:
            return []
        
        outliers = []
        X = np.array(embeddings)
        
        for i in range(n):
            # Calculate similarities with all others
            similarities = np.dot(X, X[i])
            similarities[i] = 0  # Exclude self
            
            # Check if any similarity exceeds threshold
            if np.max(similarities) < threshold:
                outliers.append(i)
        
        return outliers