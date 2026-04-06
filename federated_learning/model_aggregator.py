"""
Model aggregation for federated learning
Implements FedAvg and weighted averaging
"""
import torch
import numpy as np
from typing import List, Dict, Any, Tuple
from collections import OrderedDict
from loguru import logger


class ModelAggregator:
    """Aggregate model updates from federated learning clients"""
    
    def __init__(self, aggregation_method: str = "fedavg"):
        """
        Initialize aggregator
        
        Args:
            aggregation_method: Method to use (fedavg, weighted_avg, median)
        """
        self.aggregation_method = aggregation_method
        self.aggregation_history: List[Dict] = []
    
    def aggregate_models(
        self,
        client_models: List[Tuple[OrderedDict, int]],
        global_model: OrderedDict
    ) -> OrderedDict:
        """
        Aggregate client models into new global model
        
        Args:
            client_models: List of (model_state_dict, num_samples) tuples
            global_model: Current global model state dict
            
        Returns:
            New aggregated model state dict
        """
        if not client_models:
            logger.warning("No client models to aggregate")
            return global_model
        
        logger.info(f"Aggregating {len(client_models)} client models using {self.aggregation_method}")
        
        if self.aggregation_method == "fedavg":
            aggregated = self._federated_averaging(client_models)
        elif self.aggregation_method == "weighted_avg":
            aggregated = self._weighted_averaging(client_models)
        elif self.aggregation_method == "median":
            aggregated = self._median_aggregation(client_models)
        else:
            raise ValueError(f"Unknown aggregation method: {self.aggregation_method}")
        
        # Record aggregation
        self.aggregation_history.append({
            "num_clients": len(client_models),
            "total_samples": sum(num_samples for _, num_samples in client_models),
            "method": self.aggregation_method
        })
        
        return aggregated
    
    def _federated_averaging(
        self,
        client_models: List[Tuple[OrderedDict, int]]
    ) -> OrderedDict:
        """
        FedAvg: Weighted average by number of samples
        
        Args:
            client_models: List of (model_state_dict, num_samples)
            
        Returns:
            Aggregated model state dict
        """
        total_samples = sum(num_samples for _, num_samples in client_models)
        
        # Initialize aggregated model with zeros
        aggregated_model = OrderedDict()
        
        for key in client_models[0][0].keys():
            aggregated_model[key] = torch.zeros_like(client_models[0][0][key])
        
        # Weighted sum
        for model_state, num_samples in client_models:
            weight = num_samples / total_samples
            
            for key in model_state.keys():
                aggregated_model[key] += model_state[key] * weight
        
        logger.info(f"FedAvg completed: {len(client_models)} clients, {total_samples} total samples")
        return aggregated_model
    
    def _weighted_averaging(
        self,
        client_models: List[Tuple[OrderedDict, int]]
    ) -> OrderedDict:
        """
        Weighted averaging with custom weights
        
        Args:
            client_models: List of (model_state_dict, num_samples)
            
        Returns:
            Aggregated model state dict
        """
        # For now, same as FedAvg but can be customized
        return self._federated_averaging(client_models)
    
    def _median_aggregation(
        self,
        client_models: List[Tuple[OrderedDict, int]]
    ) -> OrderedDict:
        """
        Coordinate-wise median aggregation (robust to outliers)
        
        Args:
            client_models: List of (model_state_dict, num_samples)
            
        Returns:
            Aggregated model state dict
        """
        aggregated_model = OrderedDict()
        
        for key in client_models[0][0].keys():
            # Stack all client parameters for this layer
            stacked_params = torch.stack([
                model_state[key] for model_state, _ in client_models
            ])
            
            # Compute median
            aggregated_model[key] = torch.median(stacked_params, dim=0)[0]
        
        logger.info(f"Median aggregation completed: {len(client_models)} clients")
        return aggregated_model
    
    def compute_model_similarity(
        self,
        model1: OrderedDict,
        model2: OrderedDict
    ) -> float:
        """
        Compute cosine similarity between two models
        
        Args:
            model1: First model state dict
            model2: Second model state dict
            
        Returns:
            Similarity score (0-1)
        """
        # Flatten all parameters
        params1 = torch.cat([p.flatten() for p in model1.values()])
        params2 = torch.cat([p.flatten() for p in model2.values()])
        
        # Cosine similarity
        similarity = torch.nn.functional.cosine_similarity(
            params1.unsqueeze(0),
            params2.unsqueeze(0)
        )
        
        return float(similarity.item())
    
    def detect_outlier_clients(
        self,
        client_models: List[Tuple[OrderedDict, int]],
        threshold: float = 0.3
    ) -> List[int]:
        """
        Detect outlier client models (potential adversarial)
        
        Args:
            client_models: List of (model_state_dict, num_samples)
            threshold: Similarity threshold for outlier detection
            
        Returns:
            List of outlier client indices
        """
        if len(client_models) < 3:
            return []
        
        outliers = []
        
        # Compute pairwise similarities
        n = len(client_models)
        similarities = np.zeros((n, n))
        
        for i in range(n):
            for j in range(i + 1, n):
                sim = self.compute_model_similarity(
                    client_models[i][0],
                    client_models[j][0]
                )
                similarities[i, j] = sim
                similarities[j, i] = sim
        
        # Find clients with low average similarity
        for i in range(n):
            avg_similarity = np.mean(similarities[i, :])
            if avg_similarity < threshold:
                outliers.append(i)
                logger.warning(f"Client {i} detected as outlier (avg_sim: {avg_similarity:.3f})")
        
        return outliers
    
    def filter_outliers(
        self,
        client_models: List[Tuple[OrderedDict, int]],
        threshold: float = 0.3
    ) -> List[Tuple[OrderedDict, int]]:
        """
        Remove outlier clients before aggregation
        
        Args:
            client_models: List of (model_state_dict, num_samples)
            threshold: Similarity threshold
            
        Returns:
            Filtered list of client models
        """
        outlier_indices = self.detect_outlier_clients(client_models, threshold)
        
        if not outlier_indices:
            return client_models
        
        filtered = [
            client_models[i]
            for i in range(len(client_models))
            if i not in outlier_indices
        ]
        
        logger.info(f"Filtered {len(outlier_indices)} outlier clients")
        return filtered
    
    def compute_aggregation_metrics(
        self,
        old_model: OrderedDict,
        new_model: OrderedDict,
        client_models: List[Tuple[OrderedDict, int]]
    ) -> Dict[str, float]:
        """
        Compute metrics about the aggregation
        
        Args:
            old_model: Previous global model
            new_model: New aggregated model
            client_models: Client models used
            
        Returns:
            Dictionary of metrics
        """
        # Model change magnitude
        change_magnitude = 0.0
        for key in old_model.keys():
            diff = new_model[key] - old_model[key]
            change_magnitude += torch.norm(diff).item()
        
        # Client diversity
        if len(client_models) > 1:
            diversities = []
            for i in range(len(client_models)):
                for j in range(i + 1, len(client_models)):
                    sim = self.compute_model_similarity(
                        client_models[i][0],
                        client_models[j][0]
                    )
                    diversities.append(1.0 - sim)
            
            avg_diversity = np.mean(diversities)
        else:
            avg_diversity = 0.0
        
        return {
            "change_magnitude": change_magnitude,
            "avg_client_diversity": avg_diversity,
            "num_clients": len(client_models)
        }
    
    def get_aggregation_history(self) -> List[Dict]:
        """Get history of all aggregations"""
        return self.aggregation_history
    
    def save_aggregated_model(
        self,
        model: OrderedDict,
        filepath: str
    ):
        """Save aggregated model to file"""
        torch.save(model, filepath)
        logger.info(f"Saved aggregated model to {filepath}")
    
    def load_aggregated_model(self, filepath: str) -> OrderedDict:
        """Load aggregated model from file"""
        model = torch.load(filepath, map_location='cpu')
        logger.info(f"Loaded aggregated model from {filepath}")
        return model


class SecureAggregator(ModelAggregator):
    """Secure aggregation with privacy preservation"""
    
    def __init__(self):
        super().__init__(aggregation_method="fedavg")
        self.noise_scale = 0.001
    
    def add_differential_privacy(
        self,
        model: OrderedDict,
        epsilon: float = 1.0
    ) -> OrderedDict:
        """
        Add differential privacy noise to model
        
        Args:
            model: Model state dict
            epsilon: Privacy budget (smaller = more privacy)
            
        Returns:
            Model with added noise
        """
        noisy_model = OrderedDict()
        
        for key, param in model.items():
            # Add Gaussian noise
            noise = torch.randn_like(param) * (self.noise_scale / epsilon)
            noisy_model[key] = param + noise
        
        logger.info(f"Added differential privacy noise (epsilon={epsilon})")
        return noisy_model