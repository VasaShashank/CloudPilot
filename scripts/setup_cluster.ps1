$ErrorActionPreference = "Stop"

Write-Host "Setting up CloudPilot kind cluster..."

$clusters = kind get clusters
if ($clusters -notcontains "cloudpilot") {
    Write-Host "Creating kind cluster 'cloudpilot'..."
    kind create cluster --name cloudpilot
} else {
    Write-Host "Cluster 'cloudpilot' already exists."
}

Write-Host "Building docker image cloudpilot-workload:latest..."
docker build -t cloudpilot-workload:latest ./workloads/

Write-Host "Loading image into kind cluster..."
kind load docker-image cloudpilot-workload:latest --name cloudpilot

Write-Host "Applying Kubernetes namespace..."
kubectl apply -f ./k8s/namespace.yaml

Write-Host "CloudPilot cluster setup completed successfully!"
Write-Host "Next steps:"
Write-Host "1. Deploy the CloudPilot backend."
Write-Host "2. Submit workflows using the API."
