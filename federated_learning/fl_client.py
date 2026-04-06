"""
Federated Learning Client for Face Recognition
Each organization runs this client on their edge device
"""
import flwr as fl
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from typing import Dict, List, Tuple, Optional
import numpy as np
from pathlib import Path
import pickle

class SimpleClassifier(nn.Module):
    """Simple face verification model for FL"""
    def __init__(self, input_dim=512, num_classes=50):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        return self.fc(x)

class FaceRecognitionClient(fl.client.NumPyClient):
    def __init__(
        self,
        model: nn.Module,
        train_loader: DataLoader,
        test_loader: DataLoader,
        device: str = "cpu",
        client_id: str = "client_1"
    ):
        self.model = model.to(device)
        self.train_loader = train_loader
        self.test_loader = test_loader
        self.device = device
        self.client_id = client_id
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = optim.Adam(self.model.parameters(), lr=0.001)
    
    def get_parameters(self, config: Dict) -> List[np.ndarray]:
        """Return model parameters as a list of NumPy arrays"""
        return [val.cpu().numpy() for _, val in self.model.state_dict().items()]
    
    def set_parameters(self, parameters: List[np.ndarray]) -> None:
        """Update model with aggregated parameters from server"""
        params_dict = zip(self.model.state_dict().keys(), parameters)
        state_dict = {k: torch.tensor(v) for k, v in params_dict}
        self.model.load_state_dict(state_dict, strict=True)
    
    def fit(
        self,
        parameters: List[np.ndarray],
        config: Dict
    ) -> Tuple[List[np.ndarray], int, Dict]:
        """Train model on local data"""
        self.set_parameters(parameters)
        
        # Training loop
        self.model.train()
        epoch_loss = 0.0
        num_examples = 0
        
        epochs = config.get("epochs", 1)
        
        for epoch in range(epochs):
            for batch_idx, (data, target) in enumerate(self.train_loader):
                data, target = data.to(self.device), target.to(self.device)
                
                self.optimizer.zero_grad()
                output = self.model(data)
                loss = self.criterion(output, target)
                loss.backward()
                self.optimizer.step()
                
                epoch_loss += loss.item() * len(data)
                num_examples += len(data)
        
        # Return updated parameters and metrics
        return (
            self.get_parameters(config={}),
            num_examples,
            {"loss": epoch_loss / num_examples}
        )
    
    def evaluate(
        self,
        parameters: List[np.ndarray],
        config: Dict
    ) -> Tuple[float, int, Dict]:
        """Evaluate model on local test data"""
        self.set_parameters(parameters)
        
        self.model.eval()
        loss = 0.0
        correct = 0
        num_examples = 0
        
        with torch.no_grad():
            for data, target in self.test_loader:
                data, target = data.to(self.device), target.to(self.device)
                
                output = self.model(data)
                loss += self.criterion(output, target).item() * len(data)
                
                pred = output.argmax(dim=1, keepdim=True)
                correct += pred.eq(target.view_as(pred)).sum().item()
                num_examples += len(data)
        
        accuracy = correct / num_examples
        avg_loss = loss / num_examples
        
        return avg_loss, num_examples, {"accuracy": accuracy}

def load_local_data(
    client_id: str,
    data_path: Path
) -> Tuple[DataLoader, DataLoader]:
    """
    Load local training data for this client
    In production, this loads real face embeddings collected at this location
    """
    # For demo: generate synthetic data
    # In production: load from storage/local/client_data/
    
    # Training data
    train_embeddings = np.random.randn(100, 512).astype(np.float32)
    train_labels = np.random.randint(0, 50, 100).astype(np.int64)
    
    train_dataset = TensorDataset(
        torch.from_numpy(train_embeddings),
        torch.from_numpy(train_labels)
    )
    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    
    # Test data
    test_embeddings = np.random.randn(20, 512).astype(np.float32)
    test_labels = np.random.randint(0, 50, 20).astype(np.int64)
    
    test_dataset = TensorDataset(
        torch.from_numpy(test_embeddings),
        torch.from_numpy(test_labels)
    )
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)
    
    return train_loader, test_loader

def start_client(
    server_address: str = "localhost:8080",
    client_id: str = "client_1",
    data_path: Optional[Path] = None
):
    """Start federated learning client"""
    print(f"Starting FL Client: {client_id}")
    print(f"Connecting to server: {server_address}")
    
    # Load local data
    if data_path is None:
        data_path = Path(f"data/fl_clients/{client_id}")
    
    train_loader, test_loader = load_local_data(client_id, data_path)
    
    # Initialize model
    model = SimpleClassifier(input_dim=512, num_classes=50)
    
    # Create client
    client = FaceRecognitionClient(
        model=model,
        train_loader=train_loader,
        test_loader=test_loader,
        device="cpu",
        client_id=client_id
    )
    
    # Start client
    fl.client.start_numpy_client(
        server_address=server_address,
        client=client
    )

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Federated Learning Client")
    parser.add_argument(
        "--server",
        type=str,
        default="localhost:8080",
        help="Server address (host:port)"
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default="client_1",
        help="Client identifier"
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to local training data"
    )
    
    args = parser.parse_args()
    
    start_client(
        server_address=args.server,
        client_id=args.client_id,
        data_path=Path(args.data_path) if args.data_path else None
    )