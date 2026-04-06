#!/bin/bash

echo "Generating crypto materials..."

# Generate crypto materials using cryptogen
cryptogen generate --config=./crypto-config.yaml --output="organizations"

echo "Crypto materials generated successfully!"