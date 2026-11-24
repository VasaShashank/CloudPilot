# CloudPilot on AWS: Low-Cost K3s Demo

This is a deployment plan only. No AWS resources have been created. EC2, storage, network traffic, taxes, and public IPv4 may incur charges; confirm current prices and obtain approval before provisioning anything.

## Recommended architecture

Run CloudPilot and a **single-node K3s cluster on one EC2 instance**. CloudPilot uses Kubernetes Jobs, so a plain Docker-only host would not provide its intended orchestration. K3s avoids EKS control-plane charges and the EC2 node can execute both the API and workload Jobs. The instance is a single point of failure and is suitable for a student demo, not production/high availability.

Keep the dashboard private: CloudPilot currently has no authentication. Do not open TCP 8000, 8001, or 6443 to the internet. Use a private VPN such as Tailscale/WireGuard for both you and your friend, and restrict SSH to your own IP. The existing ClusterIP Service is intentionally not public.

The app's execution-history and audit CSV/JSONL files are written under `datasets/`. The Kubernetes deployment persists this directory in a 1 Gi PVC (initialized from the image the first time). The S3 module is an emulator, not a configured AWS S3 integration; no bucket, IAM credentials, or CloudWatch resources are required for this demo.

## Approximate monthly cost

Illustrative us-east-1 Linux On-Demand estimate, 730 hours/month, USD/INR assumed at ₹86/USD, 20 GiB gp3, one public IPv4 address, before taxes and data transfer:

| Instance | Compute | Disk + IPv4 | Approx. total |
|---|---:|---:|---:|
| `t3.medium` (2 vCPU, 4 GiB; dashboard and small demo Jobs) | ~$30.37 | ~$5.25 | **~$3,060/month** |
| `t3.large` (2 vCPU, 8 GiB; more room for Python/K3s/workloads) | ~$60.74 | ~$5.25 | **~$5,680/month** |

Assumptions use approximate list rates ($0.0416/$0.0832 per hour, gp3 $0.08/GB-month, public IPv4 $0.005/hour). Prices vary by region/date. Data transfer, taxes, CPU credit behavior, snapshots, and any optional services can increase the bill. AWS free-tier/credit eligibility is account- and date-dependent; do not assume this is free. Stop/terminate resources only after reviewing their data-retention consequences; a stopped instance can still incur EBS charges.

**Recommendation:** begin with `t3.medium` only for a short dashboard and simulated-workload demo; use `t3.large` if memory-heavy genomic jobs are required. Avoid EKS, NAT Gateway, load balancers, S3, and CloudWatch for this single-instance demo unless a concrete requirement and budget justify them.

## Provisioning checklist (only after approval)

1. In AWS, create a budget alert and confirm the current region-specific estimate in AWS Pricing Calculator.
2. Launch one Ubuntu EC2 instance (`t3.medium` or `t3.large`) with a 20 GiB gp3 root disk. Create no EKS cluster.
3. Security group: SSH (22) from your IP only. Do not add public ingress for 8000, 8001, or 6443. Configure private VPN access before sharing the dashboard.
4. SSH in, then install Docker and K3s using their official instructions. Review the K3s installer before running it:

   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io git curl
   curl -sfL https://get.k3s.io -o /tmp/install-k3s.sh
   less /tmp/install-k3s.sh
   sudo sh /tmp/install-k3s.sh
   sudo k3s kubectl get nodes
   ```

   Keep inbound port 6443 blocked at the security group; never distribute the K3s admin kubeconfig.

5. On the EC2 host, clone the repository and build/import both images into K3s containerd:

   ```bash
   git clone https://github.com/VasaShashank/CloudPilot.git
   cd CloudPilot
   docker build -t cloudpilot:latest .
   docker build -f workloads/Dockerfile -t cloudpilot-workload:latest .
   docker save cloudpilot:latest cloudpilot-workload:latest -o /tmp/cloudpilot-images.tar
   sudo k3s ctr images import /tmp/cloudpilot-images.tar
   ```

   The build context includes repository model and dataset files. Keep private genomic data out of source control and use only data you are authorized to process.

6. Apply the deployment resources:

   ```bash
   sudo k3s kubectl apply -f k8s/namespace.yaml
   sudo k3s kubectl apply -f k8s/rbac.yaml
   sudo k3s kubectl apply -f k8s/pvc.yaml
   sudo k3s kubectl apply -f k8s/deployment.yaml
   sudo k3s kubectl apply -f k8s/service.yaml
   sudo k3s kubectl rollout status deployment/cloudpilot -n cloudpilot
   sudo k3s kubectl get pods,pvc -n cloudpilot
   ```

7. Verify from the host:

   ```bash
   sudo k3s kubectl port-forward --address <EC2_VPN_IP> -n cloudpilot service/cloudpilot 8000:8000
   curl http://<EC2_VPN_IP>:8000/healthz
   curl http://<EC2_VPN_IP>:8000/api/cluster/status
   ```

   Bind the forward only to the VPN interface/address, not `0.0.0.0`. Your friend must join the same private VPN to open `http://<EC2_VPN_IP>:8000`. Configure a supervised service for the port-forward only after testing and approving that access model.

The pod uses an in-cluster service account with namespace-scoped Job/Pod permissions plus read-only node listing. It does not need the host's admin kubeconfig or AWS credentials. The PVC uses K3s local-path storage on the EC2 disk; back it up before replacing the instance or its disk.

## Before using this outside a private demo

- Add application authentication and HTTPS before exposing it beyond a trusted VPN; the API currently accepts workflow/job requests without user authentication.
- Review workflow YAML/image inputs and resource quotas before allowing untrusted users.
- Keep SSH and Kubernetes API access restricted; rotate any credentials used for image registries or VPNs.
- Configure and test backups for the PVC. An EC2 disk is not a backup.
- Confirm resource requests against actual workload needs; `t3.medium` may be insufficient for genomic processing.

No AWS provisioning, billing changes, public endpoint, or credentials are part of the local implementation completed here.
