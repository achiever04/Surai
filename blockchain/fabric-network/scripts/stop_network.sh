#!/bin/bash

echo "Stopping Hyperledger Fabric network..."

docker-compose -f docker-compose-fabric.yml down

echo "Fabric network stopped!"