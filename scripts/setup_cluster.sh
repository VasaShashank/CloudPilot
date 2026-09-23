#!/bin/bash
set -e

echo "Setting up CloudPilot kind cluster..."

if ! kind get clusters | grep -q "cloudpilot"; then
    echo "Creating kind cluster 'cloudpilot'..."
    kind create cluster --name cloudpilot
else
    echo "Cluster 'cloudpilot' already exists."
fi

echo "Building docker image cloudpilot-workload:latest..."
docker build -t cloudpilot-workload:latest ./workloads/

echo "Loading image into kind cluster..."
kind load docker-image cloudpilot-workload:latest --name cloudpilot

echo "Applying Kubernetes namespace..."
kubectl apply -f ./k8s/namespace.yaml

echo "CloudPilot cluster setup completed successfully!"
echo "Next steps:"
echo "1. Deploy the CloudPilot backend."
echo "2. Submit workflows using the API."
