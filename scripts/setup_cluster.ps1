$ErrorActionPreference = "Stop"

Write-Host "Setting up CloudPilot kind cluster..."

$hasKind = Get-Command kind -ErrorAction SilentlyContinue

if ($hasKind) {
    $clusters = kind get clusters
    if ($clusters -notcontains "cloudpilot") {
        Write-Host "Creating kind cluster 'cloudpilot'..."
        kind create cluster --name cloudpilot
    } else {
        Write-Host "Cluster 'cloudpilot' already exists."
    }
} else {
    Write-Host "Notice: 'kind' CLI was not found in PATH."
    $container = docker ps -a --filter "name=cloudpilot-control-plane" --format "{{.Names}}"
    if ($container -eq "cloudpilot-control-plane") {
        Write-Host "Found existing kind cluster container 'cloudpilot-control-plane'."
        $status = docker inspect -f '{{.State.Running}}' cloudpilot-control-plane
        if ($status -ne "true") {
            Write-Host "Starting 'cloudpilot-control-plane' container..."
            docker start cloudpilot-control-plane
        }
    } else {
        Write-Error "Neither 'kind' CLI nor 'cloudpilot-control-plane' container was found. Please install kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation"
    }
}

Write-Host "Building docker image cloudpilot-workload:latest..."
docker build -t cloudpilot-workload:latest ./workloads/

Write-Host "Loading image into kind cluster..."
if ($hasKind) {
    kind load docker-image cloudpilot-workload:latest --name cloudpilot
} else {
    Write-Host "Using containerd ctr inside kind container to import image..."
    $tarPath = Join-Path $PSScriptRoot "workload.tar"
    docker save cloudpilot-workload:latest -o $tarPath
    docker cp $tarPath cloudpilot-control-plane:/root/workload.tar
    docker exec cloudpilot-control-plane ctr --namespace=k8s.io images import /root/workload.tar
    Remove-Item $tarPath -ErrorAction SilentlyContinue
    docker exec cloudpilot-control-plane rm /root/workload.tar
}

Write-Host "Applying Kubernetes namespace..."
kubectl apply -f ./k8s/namespace.yaml

Write-Host "CloudPilot cluster setup completed successfully!"
Write-Host "Next steps:"
Write-Host "1. Deploy the CloudPilot backend."
Write-Host "2. Submit workflows using the API or CLI."
