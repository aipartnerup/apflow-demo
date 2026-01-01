#!/bin/bash
# Deployment script for apflow-demo

set -e

echo "Deploying apflow-demo..."

# Build Docker image
echo "Building Docker image..."
docker build -f docker/Dockerfile -t apflow-demo:latest .

# Run with docker-compose
echo "Starting services with docker-compose..."
docker-compose up -d

echo "Deployment complete!"
echo "API available at http://localhost:8000"

