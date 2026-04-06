import flwr as fl
from typing import List, Tuple, Dict, Optional
import numpy as np

class FederatedServer:
    def __init__(self, num_rounds: int = 10):
        self.num_rounds = num_rounds
        
    def weighted_average(self, metrics: List[Tuple[int, Dict]]) -> Dict:
        """Aggregate metrics from clients"""
        accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics]
        examples = [num_examples for num_examples, _ in metrics]
        
        return {"accuracy": sum(accuracies) / sum(examples)}
    
    def start(self, server_address: str = "localhost:8080"):
        """Start federated learning server"""
        strategy = fl.server.strategy.FedAvg(
            fraction_fit=1.0,  # Sample 100% of available clients
            fraction_evaluate=1.0,
            min_fit_clients=2,
            min_evaluate_clients=2,
            min_available_clients=2,
            evaluate_metrics_aggregation_fn=self.weighted_average,
        )
        
        fl.server.start_server(
            server_address=server_address,
            config=fl.server.ServerConfig(num_rounds=self.num_rounds),
            strategy=strategy,
        )

if __name__ == "__main__":
    server = FederatedServer(num_rounds=10)
    server.start()