import os
import sys
import time
import json
import random
import hashlib
import subprocess
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

def get_memory_mb() -> float:
    if psutil:
        return psutil.Process().memory_info().rss / (1024 * 1024)
    try:
        with open("/sys/fs/cgroup/memory.current", "r") as f:
            return int(f.read().strip()) / (1024 * 1024)
    except Exception:
        return 50.0

def get_cpu_times():
    if psutil:
        times = psutil.Process().cpu_times()
        return times.user + times.system
    return time.process_time()

def run_genomic_op(stage_type: str, vcf_path: str):
    """Run real bcftools operation on VCF if available."""
    if not os.path.exists(vcf_path):
        return None
    
    if stage_type in ("vcf_stats", "quality_control", "qc"):
        cmd = ["bcftools", "stats", vcf_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"stats_lines": len(res.stdout.splitlines())}
        
    elif stage_type in ("filtering", "preprocessing"):
        cmd = ["bcftools", "view", "-v", "snps", "-i", "MAF>0.05", vcf_path, "-o", "/tmp/filtered.vcf"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"filtered": True}
        
    elif stage_type in ("variant_processing", "alignment"):
        cmd = ["bcftools", "query", "-f", "%CHROM\\t%POS\\t%REF\\t%ALT\\n", vcf_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"extracted_variants": len(res.stdout.splitlines())}
        
    elif stage_type in ("feature_extraction", "aggregation"):
        cmd = ["bcftools", "view", "-m2", "-M2", "-v", "snps", "-c", "1", vcf_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"biallelic_snps": len(res.stdout.splitlines())}

    elif stage_type in ("analysis", "variant_analysis"):
        cmd = ["bcftools", "view", "-c", "2", vcf_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {"analyzed_lines": len(res.stdout.splitlines())}
        
    return None

def main():
    start_wall_time = time.time()
    start_cpu_time = get_cpu_times()
    
    stage_name = os.environ.get("STAGE_NAME")
    stage_type = os.environ.get("STAGE_TYPE", "unknown").lower()
    fail_stage = os.environ.get("FAIL_STAGE", "false").lower() == "true"
    
    # Workload identifiers
    workload_id = os.environ.get("WORKLOAD_ID")
    chunk_size_label = os.environ.get("CHUNK_SIZE", "small").lower()
    if not workload_id:
        if chunk_size_label in ("small", "medium", "large"):
            workload_id = f"chr22_{chunk_size_label}_full"
        else:
            workload_id = f"chr22_{chunk_size_label}"

    workload_source = os.environ.get("WORKLOAD_SOURCE", "genomic")

    if not stage_name:
        print("[CloudPilot] Error: STAGE_NAME environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"[CloudPilot] {stage_name} ({stage_type}) started [workload: {workload_id}, source: {workload_source}]")

    if fail_stage:
        print(f"[CloudPilot] Error: {stage_name} failed intentionally (FAIL_STAGE=true)", file=sys.stderr)
        sys.exit(1)

    # Check for local chunk data
    base_data_dir = Path("/app/data/chunks")
    chunk_vcf = None
    item_meta = {}
    
    meta_json = base_data_dir / "metadata.json"
    if meta_json.exists():
        try:
            with open(meta_json, "r") as f:
                all_meta = json.load(f)
                item_meta = all_meta.get(workload_id, {})
                if not item_meta and chunk_size_label in all_meta:
                    item_meta = all_meta[chunk_size_label]
        except Exception as e:
            print(f"[CloudPilot] Warning reading metadata: {e}")

    # Resolve VCF path
    env_vcf_path = os.environ.get("VCF_PATH")
    if env_vcf_path and os.path.exists(env_vcf_path):
        chunk_vcf = env_vcf_path
    elif item_meta.get("path"):
        cand = Path("/app") / item_meta["path"]
        if cand.exists():
            chunk_vcf = str(cand)
    elif item_meta.get("name"):
        cand = base_data_dir / chunk_size_label / item_meta["name"]
        if cand.exists():
            chunk_vcf = str(cand)

    # Resolve characteristics
    chromosome = str(item_meta.get("chromosome", "22"))
    region_start = int(item_meta.get("region_start", 16050000))
    region_end = int(item_meta.get("region_end", region_start + 100000))
    region_size = int(item_meta.get("region_size", region_end - region_start))
    variant_count = int(item_meta.get("variant_count", 1170))
    sample_count = int(item_meta.get("sample_count", 2504))
    dataset_size_mb = float(item_meta.get("compressed_size_mb", 0.17))

    peak_memory = get_memory_mb()

    # Perform computation
    if chunk_vcf and os.path.exists(chunk_vcf):
        print(f"[CloudPilot] Processing real genomic VCF chunk: {chunk_vcf} ({variant_count} vars, {sample_count} samples)")
        op_res = run_genomic_op(stage_type, chunk_vcf)
        if op_res:
            print(f"[CloudPilot] Genomic operation result: {op_res}")
    else:
        # Simulated workload (Phase 1 compatibility)
        if workload_source == "simulated" or stage_type in ("job", "quality_control", "preprocessing", "alignment", "analysis"):
            print(f"[CloudPilot] Running simulated workload...")
            time.sleep(random.uniform(2.0, 5.0))
            data = os.urandom(512 * 1024)
            hashlib.sha256(data).hexdigest()

    peak_memory = max(peak_memory, get_memory_mb())
    
    end_wall_time = time.time()
    end_cpu_time = get_cpu_times()
    
    runtime_seconds = round(max(0.01, end_wall_time - start_wall_time), 3)
    cpu_used = round(max(0.1, end_cpu_time - start_cpu_time), 3)
    peak_memory_mb = round(peak_memory, 2)
    
    # Emit structured profiling telemetry
    profiling_record = {
        "stage_id": stage_name,
        "stage_type": stage_type,
        "workload_id": workload_id,
        "workload_source": workload_source,
        "chromosome": chromosome,
        "region_start": region_start,
        "region_end": region_end,
        "region_size": region_size,
        "variant_count": variant_count,
        "sample_count": sample_count,
        "dataset_size_mb": dataset_size_mb,
        "runtime_seconds": runtime_seconds,
        "actual_cpu": cpu_used,
        "actual_memory_mb": peak_memory_mb,
        "success": True,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    print(f"[CloudPilot Profiling] {json.dumps(profiling_record)}")
    print(f"[CloudPilot] {stage_name} ({stage_type}) completed successfully in {runtime_seconds}s (mem: {peak_memory_mb}MB)")
    sys.exit(0)

if __name__ == "__main__":
    main()
