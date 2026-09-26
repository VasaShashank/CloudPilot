#!/bin/bash
set -e

echo "Setting up CloudPilot kind cluster..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if command -v kind &> /dev/null; then
    if ! kind get clusters | grep -q "cloudpilot"; then
        echo "Creating kind cluster 'cloudpilot'..."
        kind create cluster --name cloudpilot
    else
        echo "Cluster 'cloudpilot' already exists."
    fi
else
    echo "Notice: 'kind' CLI was not found in PATH."
    if docker ps -a --format '{{.Names}}' | grep -q "^cloudpilot-control-plane$"; then
        echo "Found existing kind cluster container 'cloudpilot-control-plane'."
        if [ "$(docker inspect -f '{{.State.Running}}' cloudpilot-control-plane)" != "true" ]; then
            echo "Starting 'cloudpilot-control-plane' container..."
            docker start cloudpilot-control-plane
        fi
    else
        echo "Error: Neither 'kind' CLI nor 'cloudpilot-control-plane' container was found."
        echo "Please install kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
        exit 1
    fi
fi

echo "Building docker image cloudpilot-workload:latest..."
docker build -t cloudpilot-workload:latest "$SCRIPT_DIR/../workloads/"

echo "Loading image into kind cluster..."
if command -v kind &> /dev/null; then
    kind load docker-image cloudpilot-workload:latest --name cloudpilot
else
    echo "Using containerd ctr inside kind container to import image..."
    TAR_PATH="$SCRIPT_DIR/workload.tar"
    docker save cloudpilot-workload:latest -o "$TAR_PATH"
    docker cp "$TAR_PATH" cloudpilot-control-plane:/root/workload.tar
    docker exec cloudpilot-control-plane ctr --namespace=k8s.io images import /root/workload.tar
    rm -f "$TAR_PATH"
    docker exec cloudpilot-control-plane rm -f /root/workload.tar
fi

echo "Applying Kubernetes namespace..."
kubectl apply -f "$SCRIPT_DIR/../k8s/namespace.yaml"

echo "CloudPilot cluster setup completed successfully!"
echo "Next steps:"
echo "1. Deploy the CloudPilot backend."
echo "2. Submit workflows using the API or CLI."
