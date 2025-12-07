#!/bin/bash
# Deployment script for aipartnerupflow-demo

set -e

echo "Deploying aipartnerupflow-demo..."

# Build Docker image
echo "Building Docker image..."
docker build -f docker/Dockerfile -t aipartnerupflow-demo:latest .

# Run with docker-compose
echo "Starting services with docker-compose..."
docker-compose up -d

echo "Deployment complete!"
echo "API available at http://localhost:8000"

