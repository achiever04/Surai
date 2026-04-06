#!/bin/bash

echo "Starting Hyperledger Fabric network..."

# Start the network
docker-compose -f docker-compose-fabric.yml up -d

echo "Waiting for network to start..."
sleep 10

# Create channel
docker exec cli peer channel create -o orderer.example.com:7050 -c surveillance-channel -f ./channel-artifacts/channel.tx

# Join peers to channel
docker exec cli peer channel join -b surveillance-channel.block

echo "Fabric network started successfully!"