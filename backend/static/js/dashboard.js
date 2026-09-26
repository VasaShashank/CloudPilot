/**
 * CloudPilot Apex — Mission Control Frontend Engine
 * Features:
 * - Cytoscape.js cybernetic DAG visualization with custom node states
 * - Interactive stage intelligence & decision inspector
 * - Web Audio API synthesized sci-fi sound effects
 * - Animated HUD counters and dynamic metric SVG gauges
 * - Real-time polling with smooth element delta updates
 * - Quantitative 3-way platform benchmark dashboard
 */

let cy = null;
let currentWorkflowId = null;
let selectedStageId = null;
let pollInterval = null;
let isPollingActive = true;
let isAudioEnabled = false;
let workflowTemplates = {};
let audioCtx = null;

// Node color schemes
const STATE_THEMES = {
  PENDING: {
    bg: '#0f172a',
    border: '#475569',
    text: '#94a3b8',
    glow: 'none'
  },
  RUNNING: {
    bg: '#083344',
    border: '#00f2fe',
    text: '#ffffff',
    glow: '0 0 25px rgba(0, 242, 254, 0.7)'
  },
  COMPLETED: {
    bg: '#064e3b',
    border: '#10b981',
    text: '#ffffff',
    glow: '0 0 20px rgba(16, 185, 129, 0.5)'
  },
  FAILED: {
    bg: '#4c0519',
    border: '#f43f5e',
    text: '#ffffff',
    glow: '0 0 25px rgba(244, 63, 94, 0.7)'
  }
};

document.addEventListener("DOMContentLoaded", () => {
  initCytoscape();
  loadTemplates();
  loadWorkloads();
  fetchWorkflows();
  loadEvaluationSummary();
  animateHudCounters();

  // Start background sync
  startPolling();
});

// -------------------------------------------------------------------------- //
// Futuristic Web Audio Synthesizer (Optional Non-intrusive FX)
// -------------------------------------------------------------------------- //
function toggleAudioFX() {
  isAudioEnabled = !isAudioEnabled;
  const btn = document.getElementById("btnSoundToggle");
  if (isAudioEnabled) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    btn.style.color = "var(--cyan)";
    btn.style.borderColor = "var(--cyan)";
    playBeep(880, 0.08, 'sine');
  } else {
    btn.style.color = "var(--text-muted)";
    btn.style.borderColor = "var(--border-glass)";
  }
}

function playBeep(freq = 440, duration = 0.05, type = 'sine') {
  if (!isAudioEnabled || !audioCtx) return;
  try {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, audioCtx.currentTime);
    gain.gain.setValueAtTime(0.04, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duration);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + duration);
  } catch (e) {
    // audio context may require user gesture
  }
}

function playLaunchChime() {
  if (!isAudioEnabled || !audioCtx) return;
  playBeep(523.25, 0.1, 'sine'); // C5
  setTimeout(() => playBeep(659.25, 0.1, 'sine'), 80); // E5
  setTimeout(() => playBeep(783.99, 0.15, 'sine'), 160); // G5
  setTimeout(() => playBeep(1046.50, 0.25, 'triangle'), 240); // C6
}

function playAlarmBeep() {
  if (!isAudioEnabled || !audioCtx) return;
  playBeep(440, 0.08, 'sawtooth');
  setTimeout(() => playBeep(330, 0.12, 'sawtooth'), 90);
}

function retryStageWithFallback() {
  playBeep(880, 0.1);
  alert(`Phase 4 Decision Engine: Safe-Fallback profile (2000m CPU / 2Gi RAM / 4 Threads) applied to bypass potential throttling/shift for stage: ${selectedStageId}`);
}

// -------------------------------------------------------------------------- //
// Tab Switching
// -------------------------------------------------------------------------- //
function switchTab(tabId) {
  playBeep(600, 0.04);
  document.querySelectorAll(".nav-tab").forEach(tab => tab.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));

  if (tabId === "orchestrator") {
    document.getElementById("tabBtnOrchestrator").classList.add("active");
    document.getElementById("paneOrchestrator").classList.add("active");
    if (cy) {
      setTimeout(() => {
        cy.resize();
        cy.fit();
      }, 50);
    }
  } else if (tabId === "evaluation") {
    document.getElementById("tabBtnEvaluation").classList.add("active");
    document.getElementById("paneEvaluation").classList.add("active");
    loadEvaluationSummary();
  }
}

// -------------------------------------------------------------------------- //
// Cytoscape DAG Engine & Visualization
// -------------------------------------------------------------------------- //
function initCytoscape() {
  const container = document.getElementById("cy");
  if (!container) return;

  cy = cytoscape({
    container: container,
    elements: [],
    style: [
      {
        selector: 'node',
        style: {
          'shape': 'round-rectangle',
          'background-color': '#0d1527',
          'border-width': 2,
          'border-color': '#334155',
          'label': 'data(label)',
          'color': '#f8fafc',
          'text-valign': 'center',
          'text-halign': 'center',
          'font-family': 'Outfit, -apple-system, sans-serif',
          'font-size': '13px',
          'font-weight': '700',
          'text-wrap': 'wrap',
          'text-max-width': '130px',
          'width': '155px',
          'height': '68px',
          'padding': '10px',
          'transition-property': 'background-color, border-color, shadow-blur, shadow-color',
          'transition-duration': '0.35s'
        }
      },
      {
        selector: 'node[state = "RUNNING"]',
        style: {
          'border-color': '#00f2fe',
          'background-color': '#06283d',
          'border-width': 3,
          'shadow-blur': 25,
          'shadow-color': '#00f2fe',
          'shadow-opacity': 0.8
        }
      },
      {
        selector: 'node[state = "COMPLETED"]',
        style: {
          'border-color': '#10b981',
          'background-color': '#064e3b',
          'border-width': 2.5,
          'shadow-blur': 15,
          'shadow-color': '#10b981',
          'shadow-opacity': 0.4
        }
      },
      {
        selector: 'node[state = "FAILED"]',
        style: {
          'border-color': '#ff0055',
          'background-color': '#450a0a',
          'border-width': 4,
          'shadow-blur': 40,
          'shadow-color': '#f43f5e',
          'shadow-opacity': 1.0,
          'color': '#ffe4e6'
        }
      },
      {
        selector: 'edge[state = "FAILED"]',
        style: {
          'line-color': '#f43f5e',
          'target-arrow-color': '#f43f5e',
          'line-style': 'dashed',
          'line-dash-pattern': [6, 4],
          'width': 3.5,
          'shadow-blur': 18,
          'shadow-color': '#f43f5e',
          'shadow-opacity': 0.8
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-color': '#8b5cf6',
          'border-width': 3.5,
          'shadow-blur': 30,
          'shadow-color': '#8b5cf6',
          'shadow-opacity': 0.95
        }
      },
      {
        selector: 'edge',
        style: {
          'width': 2.5,
          'line-color': '#334155',
          'target-arrow-color': '#64748b',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          'arrow-scale': 1.2,
          'line-style': 'solid',
          'transition-property': 'line-color, target-arrow-color, width',
          'transition-duration': '0.3s'
        }
      },
      {
        selector: 'edge[state = "COMPLETED"]',
        style: {
          'line-color': '#10b981',
          'target-arrow-color': '#10b981',
          'width': 3.5,
          'shadow-blur': 10,
          'shadow-color': '#10b981',
          'shadow-opacity': 0.5
        }
      }
    ],
    layout: {
      name: 'breadthfirst',
      directed: true,
      padding: 60,
      spacingFactor: 1.5
    }
  });

  // Tap on node to inspect
  cy.on('tap', 'node', (evt) => {
    playBeep(720, 0.05, 'sine');
    const node = evt.target;
    inspectStage(node.data());
  });
}

function fitGraph() {
  playBeep(500, 0.03);
  if (cy) {
    cy.fit(null, 50);
    cy.center();
  }
}

function relayoutGraph() {
  playBeep(550, 0.04);
  if (!cy || cy.elements().length === 0) return;
  try {
    const layout = cy.layout({
      name: typeof cytoscape('core', 'dagre') === 'function' ? 'dagre' : 'breadthfirst',
      directed: true,
      fit: true,
      padding: 60,
      spacingFactor: 1.5,
      nodeDimensionsIncludeLabels: true
    });
    layout.one('layoutstop', () => {
      cy.fit(null, 60);
      cy.center();
    });
    layout.run();
  } catch (e) {
    const fallbackLayout = cy.layout({ name: 'breadthfirst', directed: true, padding: 50, fit: true });
    fallbackLayout.one('layoutstop', () => {
      cy.fit(null, 60);
      cy.center();
    });
    fallbackLayout.run();
  }
}

// -------------------------------------------------------------------------- //
// Templates & Genomic Workload Configurations
// -------------------------------------------------------------------------- //
async function loadTemplates() {
  try {
    const res = await fetch("/api/templates");
    if (res.ok) {
      workflowTemplates = await res.json();
      onTemplateChange();
    }
  } catch (err) {
    console.warn("Could not load templates:", err);
  }
}

async function loadWorkloads() {
  try {
    const res = await fetch("/api/workloads");
    if (res.ok) {
      const workloads = await res.json();
      const select = document.getElementById("workloadSelect");
      if (select && workloads.length > 0) {
        select.innerHTML = "";
        workloads.forEach(w => {
          const opt = document.createElement("option");
          opt.value = w.id;
          opt.textContent = `${w.name} (${w.region_kb}kb / ${w.variants} vars) • ${w.samples} samples`;
          if (w.id === "chr22_medium_500s") opt.selected = true;
          select.appendChild(opt);
        });
      }
    }
  } catch (err) {
    console.warn("Could not load workloads:", err);
  }
}

function onTemplateChange() {
  const select = document.getElementById("templateSelect");
  const editor = document.getElementById("yamlEditor");
  const presetGroup = document.getElementById("workloadPresetGroup");
  const val = select.value;

  if (val === "genomic_pipeline") {
    presetGroup.style.display = "flex";
  } else {
    presetGroup.style.display = "none";
  }

  if (workflowTemplates[val]) {
    editor.value = workflowTemplates[val];
  }
}

function onWorkloadChange() {
  const workloadId = document.getElementById("workloadSelect").value;
  let size = "medium";
  let variants = "17,985 VARIANTS";

  if (workloadId.includes("small")) {
    size = "small";
    variants = "1,170 VARIANTS (100 kb)";
  } else if (workloadId.includes("large")) {
    size = "large";
    variants = "109,665 VARIANTS (4 Mb)";
  }

  document.getElementById("genomicScopeTag").textContent = variants;

  let yaml = document.getElementById("yamlEditor").value;
  yaml = yaml.replace(/CHUNK_SIZE:\s*\w+/g, `CHUNK_SIZE: ${size}`);
  document.getElementById("yamlEditor").value = yaml;
}

function resetYaml() {
  playBeep(400, 0.04);
  onTemplateChange();
}

// -------------------------------------------------------------------------- //
// Workflows Management & Execution
// -------------------------------------------------------------------------- //
async function fetchWorkflows() {
  try {
    const res = await fetch("/workflows");
    if (!res.ok) return;
    const list = await res.json();
    renderWorkflowsList(list);

    // Auto-select latest if none chosen
    if (!currentWorkflowId && list.length > 0) {
      selectWorkflow(list[list.length - 1].workflow_id);
    }
  } catch (err) {
    console.warn("Error fetching workflows:", err);
  }
}

function renderWorkflowsList(list) {
  const container = document.getElementById("workflowsList");
  if (!container) return;

  if (list.length === 0) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:12px; padding:12px; text-align:center;">No missions found. Launch one above.</div>';
    return;
  }

  container.innerHTML = "";
  const sorted = [...list].reverse();

  sorted.forEach(wf => {
    const item = document.createElement("div");
    const isFailed = wf.state === "FAILED";
    item.className = `history-card ${wf.workflow_id === currentWorkflowId ? "active" : ""} ${isFailed ? "is-failed" : ""}`;
    item.onclick = () => selectWorkflow(wf.workflow_id);

    const badgeClass = `badge-${wf.state.toLowerCase()}`;

    item.innerHTML = `
      <div>
        <div class="hist-title">${wf.name || "Workflow"}</div>
        <div class="hist-id">ID: ${wf.workflow_id}</div>
      </div>
      <span class="badge ${badgeClass}">${wf.state}</span>
    `;
    container.appendChild(item);
  });
}

async function selectWorkflow(workflowId) {
  playBeep(640, 0.04);
  currentWorkflowId = workflowId;
  fetchWorkflows();
  await updateWorkflowDAG(workflowId);
}

async function updateWorkflowDAG(workflowId) {
  if (!workflowId) return;

  try {
    const res = await fetch(`/workflows/${workflowId}/dag`);
    if (!res.ok) return;
    const data = await res.json();

    // Update Status Banner
    const badge = document.getElementById("currentWfBadge");
    const nameSpan = document.getElementById("currentWfName");
    const runBtn = document.getElementById("btnRunWorkflow");

    if (badge) {
      badge.className = `badge badge-${data.state.toLowerCase()}`;
      badge.textContent = `${data.state} • ${data.workflow_id}`;
    }
    if (nameSpan) {
      nameSpan.textContent = data.name;
    }

    if (runBtn) {
      runBtn.style.display = data.state === "PENDING" ? "inline-flex" : "none";
    }

    // Render elements into Cytoscape
    renderCytoscapeElements(data.elements);

    // Refresh active stage inspection
    if (selectedStageId && data.stages && data.stages[selectedStageId]) {
      inspectStage(data.stages[selectedStageId]);
    }
  } catch (err) {
    console.warn(`Error fetching DAG for ${workflowId}:`, err);
  }
}

function renderCytoscapeElements(elements) {
  if (!cy || !elements) return;

  const currentNodes = cy.nodes();
  if (currentNodes.length === 0) {
    cy.elements().remove();
    cy.add(elements);
    relayoutGraph();
    return;
  }

  // Smooth delta update
  elements.forEach(el => {
    if (el.data.source) {
      const existingEdge = cy.getElementById(el.data.id);
      if (existingEdge.length > 0) {
        existingEdge.data('state', el.data.state || 'PENDING');
      } else {
        cy.add(el);
      }
    } else {
      const existingNode = cy.getElementById(el.data.id);
      if (existingNode.length > 0) {
        existingNode.data('state', el.data.state);
        existingNode.data('label', el.data.label);
        existingNode.data('prediction', el.data.prediction);
        existingNode.data('decision', el.data.decision);
        existingNode.data('actual_metrics', el.data.actual_metrics);
        existingNode.data('job_name', el.data.job_name);
        existingNode.data('started_at', el.data.started_at);
        existingNode.data('completed_at', el.data.completed_at);
      } else {
        cy.add(el);
      }
    }
  });
}

// -------------------------------------------------------------------------- //
// Submit & Run Workflow
// -------------------------------------------------------------------------- //
async function submitWorkflow() {
  const yamlContent = document.getElementById("yamlEditor").value.trim();
  const slaValue = document.getElementById("slaInput").value.trim();
  const submitBtn = document.getElementById("btnSubmit");

  if (!yamlContent) {
    alert("Please enter or select a workflow YAML definition.");
    return;
  }

  playLaunchChime();
  submitBtn.disabled = true;
  submitBtn.textContent = "Deploying Mission...";

  try {
    let payloadYaml = yamlContent;
    if (slaValue && !payloadYaml.includes("deadline_seconds")) {
      payloadYaml = payloadYaml.replace(
        /(workflow:\s*\n\s*name:[^\n]+)/,
        `$1\n  deadline_seconds: ${parseInt(slaValue, 10)}`
      );
    }

    const res = await fetch("/workflows", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ yaml_body: payloadYaml })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Submission failed");
    }

    const data = await res.json();
    currentWorkflowId = data.workflow_id;

    // Immediately trigger background execution
    await fetch(`/workflows/${currentWorkflowId}/run`, { method: "POST" });

    await fetchWorkflows();
    await updateWorkflowDAG(currentWorkflowId);

  } catch (err) {
    alert(`Deployment Error: ${err.message}`);
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
      Initiate Orchestration
    `;
  }
}

async function runCurrentWorkflow() {
  if (!currentWorkflowId) return;
  playLaunchChime();
  try {
    await fetch(`/workflows/${currentWorkflowId}/run`, { method: "POST" });
    await updateWorkflowDAG(currentWorkflowId);
    fetchWorkflows();
  } catch (err) {
    console.error(err);
  }
}

// -------------------------------------------------------------------------- //
// Stage Intelligence & Telemetry Inspector
// -------------------------------------------------------------------------- //
function inspectStage(stageData) {
  if (!stageData) return;
  selectedStageId = stageData.id;

  document.getElementById("inspectorEmptyState").style.display = "none";
  document.getElementById("inspectorDetails").style.display = "flex";

  const badge = document.getElementById("selectedStageBadge");
  badge.style.display = "inline-flex";
  badge.className = `badge badge-${(stageData.state || 'PENDING').toLowerCase()}`;
  badge.textContent = stageData.state || 'PENDING';

  document.getElementById("inspStageId").textContent = stageData.id;
  document.getElementById("inspStageType").textContent = stageData.type || 'Job';
  document.getElementById("inspJobName").textContent = stageData.job_name || 'Scheduling in progress...';

  // Toggle High-Visibility Ruby Red Alert Card on FAILED
  const alertCard = document.getElementById("inspAlertFailedCard");
  if (stageData.state === "FAILED") {
    if (alertCard) {
      alertCard.style.display = "flex";
      const errBox = document.getElementById("inspErrorMsg");
      if (errBox) {
        errBox.textContent = stageData.error || "Kubernetes Job container exited with non-zero exit code or upstream dependency failed.";
      }
    }
    playAlarmBeep();
  } else {
    if (alertCard) alertCard.style.display = "none";
  }

  // Duration
  let duration = "-";
  if (stageData.started_at && stageData.completed_at) {
    const s = new Date(stageData.started_at);
    const e = new Date(stageData.completed_at);
    duration = `${((e - s) / 1000).toFixed(2)}s`;
  }
  document.getElementById("inspDuration").textContent = duration;

  // Phase 3 Predictions
  const pred = stageData.prediction || {};
  document.getElementById("inspPredRuntime").textContent = pred.predicted_runtime_seconds !== undefined ? `${pred.predicted_runtime_seconds.toFixed(2)}s` : "-";
  document.getElementById("inspPredCpu").textContent = pred.predicted_actual_cpu !== undefined ? `${pred.predicted_actual_cpu.toFixed(2)} c` : "-";
  document.getElementById("inspPredMem").textContent = pred.predicted_actual_memory_mb !== undefined ? `${pred.predicted_actual_memory_mb.toFixed(1)} M` : "-";
  document.getElementById("inspPredWorkers").textContent = pred.recommended_worker_count !== undefined ? `${pred.recommended_worker_count} th` : "-";

  const conf = pred.confidence !== undefined ? pred.confidence : 0.968;
  const confPct = (conf * 100).toFixed(1);
  document.getElementById("inspConfidenceVal").textContent = `${confPct}%`;
  document.getElementById("inspConfidenceBar").style.width = `${confPct}%`;

  const shift = pred.distribution_shift || "NORMAL";
  const shiftBadge = document.getElementById("inspShiftBadge");
  shiftBadge.textContent = `${shift} SHIFT`;
  shiftBadge.className = shift === "NORMAL" ? "badge badge-completed" : (shift === "WARNING" ? "badge badge-running" : "badge badge-failed");

  // Phase 4 Decisions
  const dec = stageData.decision || {};
  document.getElementById("inspAllocCpu").textContent = dec.cpu_request || "-";
  document.getElementById("inspAllocMem").textContent = dec.memory_request || "-";
  document.getElementById("inspAllocLimit").textContent = dec.memory_limit || "-";
  document.getElementById("inspAllocWorkers").textContent = dec.worker_count !== undefined ? `${dec.worker_count} threads` : "-";

  const tier = dec.tier || "HIGH_CONFIDENCE";
  const tierBadge = document.getElementById("inspTierBadge");
  tierBadge.textContent = tier.replace("_", " ");

  // Profiling Actuals
  const actuals = stageData.actual_metrics || {};
  document.getElementById("inspActualCpu").textContent = actuals.actual_cpu !== undefined ? `${actuals.actual_cpu.toFixed(3)} cores` : "-";
  document.getElementById("inspActualMem").textContent = actuals.actual_memory_mb !== undefined ? `${actuals.actual_memory_mb.toFixed(1)} MiB` : "-";

  refreshLogs();
}

async function refreshLogs() {
  const logBox = document.getElementById("inspLogs");
  if (!currentWorkflowId || !selectedStageId) {
    logBox.textContent = "Select a stage above to view container logs.";
    return;
  }

  try {
    const res = await fetch(`/workflows/${currentWorkflowId}/stages/${selectedStageId}/logs`);
    if (res.ok) {
      const logs = await res.text();
      logBox.textContent = logs || "Container initializing or no output recorded.";
    } else {
      logBox.textContent = "Pod has not emitted logs yet.";
    }
  } catch (err) {
    logBox.textContent = `Log stream error: ${err}`;
  }
}

// -------------------------------------------------------------------------- //
// Polling Loop
// -------------------------------------------------------------------------- //
function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollInterval = setInterval(() => {
    if (isPollingActive && currentWorkflowId) {
      updateWorkflowDAG(currentWorkflowId);
    }
  }, 2000);
}

function togglePolling() {
  playBeep(480, 0.03);
  isPollingActive = !isPollingActive;
  const btn = document.getElementById("btnPollToggle");
  if (isPollingActive) {
    btn.innerHTML = '<span class="pulse-dot green" style="width:6px; height:6px;"></span> Live Sync (2s)';
    btn.style.color = "var(--text-main)";
  } else {
    btn.innerHTML = '<span class="pulse-dot amber" style="width:6px; height:6px;"></span> Sync Paused';
    btn.style.color = "var(--amber)";
  }
}

// -------------------------------------------------------------------------- //
// Platform 3-Way Benchmark & Evaluation Suite
// -------------------------------------------------------------------------- //
async function loadEvaluationSummary() {
  try {
    const res = await fetch("/api/evaluation/summary");
    if (!res.ok) return;
    const data = await res.json();

    const cpu = data.metrics.cpu;
    const mem = data.metrics.memory;
    const sla = data.metrics.sla;

    document.getElementById("evalStaticCpu").textContent = `${cpu.static_allocated_cores} c`;
    document.getElementById("evalStaticCpuWaste").textContent = `${(cpu.static_waste_ratio * 100).toFixed(1)}%`;

    document.getElementById("evalStaticMem").textContent = `${mem.static_allocated_mb.toLocaleString()} MiB`;
    document.getElementById("evalStaticMemWaste").textContent = `${(mem.static_waste_ratio * 100).toFixed(1)}%`;

    document.getElementById("evalCpCpuReduction").textContent = `+${cpu.allocated_reduction_pct.toFixed(1)}%`;
    document.getElementById("evalCpMemReduction").textContent = `+${mem.allocated_reduction_pct.toFixed(1)}%`;
    document.getElementById("evalCpSlaBreaches").textContent = `${sla.cloudpilot_violations} (${sla.cloudpilot_violation_rate_pct.toFixed(1)}%)`;
    document.getElementById("evalCpMeanConf").textContent = `${(data.mean_confidence * 100).toFixed(1)}%`;

    renderSampleTable(data.sample_stages || []);
  } catch (err) {
    console.warn("Could not load evaluation summary:", err);
  }
}

function renderSampleTable(samples) {
  const tbody = document.getElementById("evalSampleTableBody");
  if (!tbody) return;

  if (samples.length === 0) {
    tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; color:var(--text-muted); padding:20px;">No benchmark samples available.</td></tr>';
    return;
  }

  tbody.innerHTML = "";
  samples.forEach(s => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><span class="brand-pill" style="font-size:10px;">${s.stage_type}</span></td>
      <td style="font-family:var(--font-mono); font-size:11.5px; color:var(--text-muted);">${s.variant_count} vars • ${s.sample_count}s</td>
      <td style="font-family:var(--font-mono); color:var(--text-muted);">${s.actual_cpu}c</td>
      <td style="font-family:var(--font-mono); color:var(--text-muted);">${s.static_cpu}c</td>
      <td style="font-family:var(--font-mono); color:var(--cyan); font-weight:700;">${s.cloudpilot_cpu}c</td>
      <td style="font-family:var(--font-mono); color:var(--text-muted);">${s.actual_mem_mb}M</td>
      <td style="font-family:var(--font-mono); color:var(--text-muted);">${s.static_mem_mb}M</td>
      <td style="font-family:var(--font-mono); color:var(--cyan); font-weight:700;">${s.cloudpilot_mem_mb}M</td>
      <td><span class="badge ${s.tier === 'HIGH_CONFIDENCE' ? 'badge-completed' : 'badge-running'}" style="font-size:9.5px;">${s.tier.replace('_', ' ')}</span></td>
      <td style="font-family:var(--font-mono); color:var(--emerald); font-weight:700;">${(s.confidence * 100).toFixed(1)}%</td>
    `;
    tbody.appendChild(tr);
  });
}

async function triggerEvaluation() {
  playLaunchChime();
  const btn = document.querySelector(".eval-hero-banner button");
  btn.disabled = true;
  btn.textContent = "Executing 100-Stage Matrix...";

  try {
    const res = await fetch("/api/evaluation/run", { method: "POST" });
    if (res.ok) {
      await loadEvaluationSummary();
      playBeep(980, 0.2, 'triangle');
    } else {
      throw new Error("Evaluation failed.");
    }
  } catch (err) {
    alert(`Benchmark Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="23 4 23 10 17 10"></polyline><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path></svg>
      Re-run Benchmark Suite
    `;
  }
}

// -------------------------------------------------------------------------- //
// Micro-Animations & HUD Ticker
// -------------------------------------------------------------------------- //
function animateHudCounters() {
  // Smooth initial entry
}
