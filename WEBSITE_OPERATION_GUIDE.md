# 🖥️ CloudPilot Apex: Complete Website & Dashboard Operation Guide
### Step-by-Step Manual for Launching, Navigating, Demonstrating, and Defending the Web Interface

---

## 📑 Table of Contents
1. [Quickstart: How to Launch the Website](#1-quickstart-how-to-launch-the-website)
2. [Interface Layout Overview](#2-interface-layout-overview)
3. [Top Status Bar & Executive HUD Ribbon](#3-top-status-bar--executive-hud-ribbon)
4. [Tab 1: Live Orchestrator (Mission Control) Deep Dive](#4-tab-1-live-orchestrator-mission-control-deep-dive)
   - [Left Column: Workflow Cockpit](#left-column-workflow-cockpit)
   - [Center Column: Cytoscape.js DAG Studio](#center-column-cytoscapejs-dag-studio)
   - [Right Column: Stage Intelligence Inspector](#right-column-stage-intelligence-inspector)
5. [Tab 2: 3-Way Empirical Benchmark Deep Dive](#5-tab-2-3-way-empirical-benchmark-deep-dive)
6. [Cloud Observability & FinOps Endpoints](#6-cloud-observability--finops-endpoints)
7. [Step-by-Step 5-Minute Live Demonstration Script](#7-step-by-step-5-minute-live-demonstration-script)
8. [Troubleshooting & Common FAQs](#8-troubleshooting--common-faqs)

---

## 1. Quickstart: How to Launch the Website

You can launch the dashboard locally on your machine with **$0 cloud cost** and **no external dependencies**.

### Step 1: Open Terminal and Activate Environment
```bash
# Navigate to the repository root
cd c:\Users\basav\Downloads\CLOUD\cloudpilot

# Activate virtual environment if using one
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate
```

### Step 2: Start the FastAPI Backend Server
```bash
python backend/main.py serve
```
You will see:
```text
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 3: Open in Any Modern Browser
Open Google Chrome, Brave, Edge, or Firefox and go to:
👉 **`http://localhost:8000/`** or **`http://localhost:8000/dashboard`**

---

## 2. Interface Layout Overview

The CloudPilot Apex interface is built with an aerospace-grade **glassmorphic dark cybernetic theme** designed to display real-time Kubernetes scheduling intelligence.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [LOGO] CLOUDPILOT APEX MISSION v5.0    [Orchestrator | 3-Way Benchmark]   kind: Online | ML: Armed │
├────────────────────────────────────────────────────────────────────────────────────────────────┤
│ [CPU +23.4%] [RAM Slashed 91.0%] [Certainty 96.8%] [SLA 0.0%] [FinOps $142.50] [Carbon -38.4%] │
├───────────────────────────────┬────────────────────────────────┬───────────────────────────────┤
│        LEFT COLUMN            │         CENTER COLUMN          │         RIGHT COLUMN          │
│       WORKFLOW COCKPIT        │       CYTOSCAPE.JS STUDIO      │       STAGE INTELLIGENCE      │
│                               │                                │                               │
│ • Architecture Templates      │ • Interactive Interactive DAG  │ • Stage Details & Node Type   │
│ • Chromosome 22 Slice Presets │ • Node States (Run/Done/Fail)  │ • Phase 3 Neural Predictions  │
│ • SLA Target Deadline Budget  │ • Animated Radar Halos         │ • Certainty & Drift Badges    │
│ • Live Manifest Editor (YAML) │ • Dock Controls (Fit/Auto)     │ • Phase 4 Sizing & Headroom   │
│ • [Initiate Orchestration]    │ • Real-time 2s Polling Toggle  │ • Live Measured Telemetry     │
│ • Chaos Monkey Fault Inject   │                                │ • Container Log Terminal      │
│ • Cluster Bin-Packing Visual  │                                │                               │
│ • Mission History Feed        │                                │                               │
└───────────────────────────────┴────────────────────────────────┴───────────────────────────────┘
```

---

## 3. Top Status Bar & Executive HUD Ribbon

### Header Elements (Top Row)
1. **Brand Identity**: `CLOUDPILOT APEX • MISSION v5.0` with chromosome 22 genomic badge.
2. **Tab Switcher Buttons**:
   - **Live Orchestrator (Mission Control)**: Interactive DAG submission, execution, and inspection.
   - **3-Way Empirical Benchmark**: Quantitative comparison against static and unmanaged baselines.
3. **Telemetry Status Chips**:
   - `kind-cluster: Online (1.31)`: Green pulsing dot indicating Kubernetes cluster availability.
   - `ML Engine: Armed (96.8% cert)`: Cyan pulsing dot confirming Random Forest & XGBoost model readiness.
4. **Futuristic Audio FX Toggle (Speaker Icon)**:
   - Click to toggle Web Audio API synthesized sci-fi sound effects (launch whoosh, node completion chime, warning klaxon, click clicks).

### Executive HUD Ribbon (6 Live Metric Gauges)
1. **CPU Core Optimization (`+23.4%` to `+31.4%`)**:
   - Shows percentage reduction in CPU cores allocated compared to standard static 1.0-core provisioning.
2. **Memory Waste Slashed (`91.0%`)**:
   - Shows percentage of memory waste eliminated compared to fixed 1024 MiB allocations.
3. **Mean Neural Confidence (`96.8%`)**:
   - Displays average certainty score across all Random Forest tree variance distributions.
4. **SLA Breach Guardian (`0.0%`)**:
   - Rate of stages that experienced deadline violations or OOMKill terminations.
5. **FinOps Projected Savings (`$142.50`)**:
   - Estimated monthly cost savings for 5,000 genomic pipeline executions calculated via AWS US-East-1 EC2 standard pricing ($0.0404/core-hour, $0.0050/GB-hour).
6. **Green Cloud Carbon Slashed (`-38.4%` / `248.5g CO₂e`)**:
   - Real-time greenhouse gas emissions reduction calculated from actual container CPU/RAM power draw and regional grid carbon intensity (GSF standard).

---

## 4. Tab 1: Live Orchestrator (Mission Control) Deep Dive

### Left Column: Workflow Cockpit

1. **Pipeline Architecture (Dropdown)**:
   - `🧬 5-Stage Live Genomic Pipeline (bcftools)`: The flagship pipeline (`vcf_stats` $\rightarrow$ `filtering` $\rightarrow$ `variant_processing` $\rightarrow$ `feature_extraction` $\rightarrow$ `analysis`).
   - `➡️ Linear 4-Stage Chain`: Sequential 4-stage dependency demo.
   - `💠 Parallel Diamond Pipeline`: Diamond DAG demonstrating concurrent branch execution.
   - `✍️ Custom Workflow Manifest`: Allows you to write and execute any custom DAG YAML.
2. **Chromosome 22 Genomic Slice (Dropdown)**:
   - Choose from 9 real regional and cohort variations:
     - `chr22 Small (100 kb / 1,170 vars) • 100 samples`
     - `chr22 Medium (1 Mb / 17,985 vars) • 500 samples` (Recommended demo preset)
     - `chr22 Large (4 Mb / 109,665 vars) • 2,504 samples` (High-load dense variant test)
   - Selecting a preset automatically injects genomic environment variables into the YAML manifest.
3. **Phase 4 SLA Deadline Budget (Number Input)**:
   - Set total workflow budget in seconds (e.g. `60`).
   - If the critical path exceeds 80% of this budget, the Decision Engine activates **Deadline Pressure**, doubling container threads.
4. **workflow.manifest.yaml (Code Editor)**:
   - Full live syntax-highlighted textarea. You can edit stage commands, CPU, memory, or dependencies in real time.
   - Click **"Reset"** to return to the clean default template.
5. **"Initiate Orchestration" (Master Launch Button)**:
   - Validates the YAML DAG structure for circular cycles via NetworkX.
   - Submits jobs to Kubernetes and triggers background scheduling.
6. **Chaos Engineering Fault Injection Panel**:
   - **⚡ Spot Preempt**: Simulates an AWS Spot 2-minute kill notice on a running stage; triggers self-healing pod migration.
   - **💥 OOMKill Surge**: Artificially exhausts container memory; tests autonomous Tier-3 Fallback escalation.
   - **Self-Healing Banner**: Displays the recovery action and recovery time in seconds (e.g., `Recovered in 2.1s`).
7. **Cluster Bin-Packing Visualizer (Karpenter Style)**:
   - Displays live resource packing across simulated nodes:
     - `c5.xlarge (Spot)`: 42% CPU, 18% RAM (2 pods)
     - `r5.xlarge (On-Demand)`: 58% CPU, 31% RAM (2 pods)
8. **Mission History Feed**:
   - Lists all previously submitted workflows with timestamp, state pill (`COMPLETED`, `RUNNING`, `FAILED`), and stage count.

---

### Center Column: Cytoscape.js DAG Studio

1. **Interactive Graph Canvas**:
   - Displays pipeline stages as interactive cybernetic nodes connected by directed arrows.
   - **Node States**:
     - ⚪ **Slate Gray Border**: `PENDING` (waiting for upstream parent stages).
     - 🟡/🔵 **Pulsing Cyan Halo**: `RUNNING` (actively executing on Kubernetes).
     - 🟢 **Glowing Emerald Green**: `COMPLETED` (finished with valid telemetry recorded).
     - 🔴 **Neon Rose Red**: `FAILED` (encountered error or intentionally failed).
2. **Floating Control Dock (Top Toolbar)**:
   - **Center View**: Centers and fits the graph into the viewport.
   - **Auto-Align**: Re-runs the Dagre layout algorithm to organize stages top-to-bottom.
   - **Live Sync (2s)**: Green pulsing dot indicating live polling. Click to pause or resume real-time updates.

---

### Right Column: Stage Intelligence Inspector

Click **any stage node** in the Cytoscape graph to open its full technical breakdown:

1. **Selected Stage Header**:
   - Shows Stage ID (e.g. `variant_processing`), Stage Type, and Status pill.
   - Displays recommended **Heterogeneous Node Type** (e.g., `r5.xlarge` for memory stages, `c5.xlarge` for compute stages).
2. **Phase 3 Neural Regressors**:
   - **Predicted Runtime**: Expected execution time in seconds.
   - **Predicted CPU Core**: Estimated CPU utilization (e.g., `0.52 cores`).
   - **Predicted Memory**: Estimated RAM demand (e.g., `66.0 MiB`).
   - **Optimal Threads**: Recommended container thread concurrency.
   - **Model Certainty Gauge**: Tree-variance certainty percentage bar (e.g., `96.8%`).
   - **Distribution Shift Badge**: Shows `NORMAL SHIFT`, `WARNING`, or `SHIFTED` based on Mahalanobis distance.
3. **Phase 4 Decision Engine Allocation**:
   - **CPU Request**: Exact Kubernetes `requests.cpu` injected.
   - **Memory Request**: Exact Kubernetes `requests.memory` injected.
   - **K8s Memory Limit**: Upper boundary ceiling (`limits.memory`) to prevent OOMKills.
   - **Allocation Headroom Stack (Visual Bar)**:
     - Blue portion: Base predicted requirement.
     - Violet portion: +25% to +60% safety margin.
     - Amber portion: K8s OOM hard ceiling cap.
4. **Live Profiling Actuals**:
   - Displays real measured CPU core utilization and peak memory usage extracted from container logs.
5. **Container Log Stream (Terminal Window)**:
   - Real-time dark terminal box streaming live stdout/stderr logs from the container pod.
   - Displays the structured `[CloudPilot Profiling]` JSON line.
   - Click **"Refresh Stream"** to fetch the latest log buffer.

---

## 5. Tab 2: 3-Way Empirical Benchmark Deep Dive

Click **"3-Way Empirical Benchmark"** in the top navigation bar to open the quantitative evaluation battleground:

### The 3 Strategy Cards
1. **Baseline 1: Static Allocation (Fixed Standard Sizing)**:
   - Allocates a fixed `1000m CPU` (1.0 core) and `1024 MiB RAM` to every single container.
   - **The Problem**: Results in massive **91.0% memory waste** on small stages and high risk of SLA breaches on heavy variant stages.
2. **Baseline 2: Unmanaged Kubernetes (Zero Requests/Limits)**:
   - Pods are submitted without requests or limits, competing for shared host CPU and memory.
   - **The Problem**: Severe noisy-neighbor contention risk and **critical OOMKill eviction risk** under concurrent pipelines.
3. **Baseline 3: CloudPilot Apex (Predictive Sizing + Headroom)**:
   - Dynamically injects predicted actuals + safety headroom (+25% to +75%).
   - **The Outcome**: **~91% memory waste reduction**, **24–31% CPU savings**, and **0.0% SLA breach rate**.

### Production Stage Sizing Matrix Table
A comprehensive row-by-row table comparing real bioinformatics stages:
- **Columns**: `Stage Type`, `Genomic Scope`, `Actual CPU`, `Static CPU`, `CloudPilot CPU`, `Actual RAM`, `Static RAM`, `CloudPilot RAM`, `Decision Tier`, `Certainty`.
- **Interactive Action**: Click **"Re-run Benchmark Suite"** in the hero banner to trigger a fresh re-run of `scripts/evaluate_platform.py` across all evaluation records.

---

## 6. Cloud Observability & FinOps Endpoints

In addition to the visual dashboard, you can open these REST/Prometheus endpoints in your browser or curl them:

1. **Prometheus Metrics**:
   - URL: `http://localhost:8000/metrics`
   - Returns standard Prometheus plain-text exposition metrics for CPU waste ratio, memory waste ratio, self-healing events, and SLA violations.
2. **FinOps Cost Summary**:
   - URL: `http://localhost:8000/api/finops/summary`
   - Returns JSON containing AWS EC2 dollar costs, core-hours saved, GB-hours saved, and monthly dollar projections.
3. **Heterogeneous Node Inventory**:
   - URL: `http://localhost:8000/api/cluster/nodes`
   - Returns simulated/live cloud VM node instance types (`c5.xlarge`, `r5.xlarge`, Spot lifecycle).
4. **Cloud Object Storage (S3 Emulator)**:
   - URL: `http://localhost:8000/api/storage/objects`
   - Lists S3 objects (`s3://cloudpilot-genomics/chunks/...`) with size metadata and presigned URL access.

---

## 7. Step-by-Step 5-Minute Live Demonstration Script

Follow this script when demonstrating the project to an audience, interviewer, or professor:

### Minute 1: The Pitch & HUD Ribbon
1. Open `http://localhost:8000/`.
2. **Say**: *"CloudPilot Apex is an autonomous Kubernetes orchestrator for heavy data pipelines. Standard cloud workflows either overprovision by 90% wasting cloud budget, or underprovision and crash with Out-Of-Memory errors."*
3. Point to the top HUD gauges:
   - Point to **CPU Optimization (+23.4%)** and **Memory Slashed (91.0%)**.
   - Point to **FinOps Projected Savings ($142.50)**: *"This represents our monthly cost savings under standard AWS EC2 pricing."*

### Minute 2: Workflow Setup & Submission
1. In the **Pipeline Architecture** dropdown, select `🧬 5-Stage Live Genomic Pipeline (bcftools)`.
2. In the **Chromosome 22 Genomic Slice** dropdown, select `chr22 Medium (1 Mb / 17,985 vars) • 500 samples`.
3. **Say**: *"Notice how the manifest editor dynamically populates with chromosome 22 regional dimensions and stage dependencies."*
4. Click **"Initiate Orchestration"**.

### Minute 3: Real-Time DAG Execution
1. Watch the Cytoscape graph update live.
2. **Say**: *"Our NetworkX DAG engine validates dependencies, detects circular cycles, and submits Kubernetes Jobs. Notice the pulsing cyan border indicating an active running container on our Kubernetes cluster."*
3. Watch the nodes transition to glowing emerald green as stages finish.

### Minute 4: Stage Intelligence & Decision Sizing
1. Click on the completed `variant_processing` node.
2. In the right panel, point to:
   - **Phase 3 Neural Regressors**: *"Our XGBoost model predicted 1.25 CPU cores and 122 MiB RAM with 96.8% certainty."*
   - **Phase 4 Decision Engine**: *"Because confidence was high and drift was normal, Tier 1 sizing was selected, allocating +25% safety headroom and a hard memory limit."*
   - **Container Log Stream**: Scroll down to show the live `[CloudPilot Profiling]` line emitted by the container.

### Minute 5: 3-Way Benchmark & Self-Healing Defense
1. Click the **"3-Way Empirical Benchmark"** tab in the top header.
2. Show the side-by-side comparison between **Static Provisioning**, **Unmanaged Kubernetes**, and **CloudPilot**.
3. **Conclude**: *"CloudPilot delivers ~91% memory waste reduction, 0% SLA breaches, automated self-healing, and workload migration—running 100% locally on Docker with zero cloud cost."*

---

## 8. Troubleshooting & Common FAQs

### Q: The DAG nodes stay in PENDING state. What should I check?
- Ensure the backend server is running (`python backend/main.py serve`).
- Verify that live polling is active (the dock button should display `Live Sync (2s)` with a green pulsing dot).

### Q: Can I run this without Docker installed?
- Yes! The FastAPI backend, ML models, DAG scheduler, 3-way evaluation benchmark, FinOps billing, S3 emulator, and unit test suite can run in offline mock mode without needing a live Docker daemon.

### Q: How do I test the futuristic sound effects?
- Click the speaker icon in the top right corner of the header. Click on any node, switch tabs, or launch a workflow to hear the synthesized audio feedback.

---

*Authored for the CloudPilot Apex Project • 2026*
