#!/usr/bin/env python3
"""
scripts/extract_genomic_chunks.py

Extracts reproducible genomic chunks with controlled region-size AND sample-count
variations from the raw 1000 Genomes chr22 VCF without uncompressing the raw dataset.
Uses bcftools and tabix (either natively or via the cloudpilot-workload Docker container).
"""

import os
import sys
import csv
import json
import shutil
import subprocess
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT_DIR / "data" / "genomic" / "raw"
CHUNKS_DIR = ROOT_DIR / "data" / "genomic" / "chunks"
SAMPLES_DIR = ROOT_DIR / "data" / "genomic" / "samples"

# Controlled Genomic Regions on chr22
REGIONS = {
    "small": {
        "chromosome": "22",
        "start": 16050000,
        "end": 16150000,
        "size": 100000,
        "region_str": "22:16050000-16150000"
    },
    "medium": {
        "chromosome": "22",
        "start": 16050000,
        "end": 17050000,
        "size": 1000000,
        "region_str": "22:16050000-17050000"
    },
    "large": {
        "chromosome": "22",
        "start": 16050000,
        "end": 20050000,
        "size": 4000000,
        "region_str": "22:16050000-20050000"
    }
}

# Controlled Sample Levels
SAMPLE_LEVELS = {
    "100s": 100,
    "500s": 500,
    "full": 2504
}

def find_raw_vcf() -> Path:
    if not RAW_DIR.exists():
        # Fallback to genome
        alt_raw = ROOT_DIR / "data" / "genome" / "raw"
        if alt_raw.exists():
            vcfs = list(alt_raw.glob("*.vcf.gz"))
            if vcfs:
                return vcfs[0]
        raise FileNotFoundError(f"Raw directory not found: {RAW_DIR}")
    
    vcfs = list(RAW_DIR.glob("*.vcf.gz"))
    if not vcfs:
        raise FileNotFoundError(f"No .vcf.gz found in {RAW_DIR}")
    
    vcf = vcfs[0]
    tbi = Path(str(vcf) + ".tbi")
    if not tbi.exists():
        raise FileNotFoundError(f"Index file not found for {vcf}. Expected {tbi}")
    return vcf

def run_cmd(cmd_list: list[str]) -> str:
    """Run command either natively or fall back to Docker container."""
    has_bcftools = shutil.which("bcftools") is not None
    
    if has_bcftools and not os.environ.get("FORCE_DOCKER_TOOLS"):
        res = subprocess.run(cmd_list, capture_output=True, text=True, check=True)
        return res.stdout
    else:
        workspace = str(ROOT_DIR)
        docker_cmd = [
            "docker", "run", "--rm",
            "-v", f"{workspace}:/workspace",
            "-w", "/workspace",
            "cloudpilot-workload:latest"
        ] + cmd_list
        res = subprocess.run(docker_cmd, capture_output=True, text=True, check=True)
        return res.stdout

def prepare_sample_lists(raw_vcf: Path):
    """Extract deterministic sample subsets from the raw VCF."""
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    rel_raw = raw_vcf.relative_to(ROOT_DIR).as_posix()
    
    query_cmd = ["bcftools", "query", "-l", rel_raw]
    all_samples = run_cmd(query_cmd).strip().splitlines()
    total_samples = len(all_samples)
    print(f"[CloudPilot] Total samples in raw dataset: {total_samples}")
    
    sample_files = {}
    for level_key, count in SAMPLE_LEVELS.items():
        if count >= total_samples:
            sample_files[level_key] = None  # None indicates use all samples without filtering
        else:
            subset = all_samples[:count]
            sample_file = SAMPLES_DIR / f"samples_{count}.txt"
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("\n".join(subset) + "\n")
            sample_files[level_key] = sample_file.relative_to(ROOT_DIR).as_posix()
            print(f"  + Prepared sample subset file ({count} samples): {sample_files[level_key]}")
            
    return sample_files

def extract_chunks():
    raw_vcf = find_raw_vcf()
    rel_raw = raw_vcf.relative_to(ROOT_DIR).as_posix()
    raw_size_mb = raw_vcf.stat().st_size / (1024 * 1024)
    print(f"[CloudPilot] Using raw compressed VCF: {rel_raw} ({raw_size_mb:.2f} MB)")
    
    sample_files = prepare_sample_lists(raw_vcf)
    
    metadata = {}
    csv_rows = []
    
    for r_key, r_info in REGIONS.items():
        for s_key, s_count in SAMPLE_LEVELS.items():
            workload_id = f"chr22_{r_key}_{s_key}"
            out_dir = CHUNKS_DIR / r_key
            out_dir.mkdir(parents=True, exist_ok=True)
            
            out_filename = f"chr22_{r_key}_{s_key}.vcf.gz"
            out_vcf = out_dir / out_filename
            rel_out = out_vcf.relative_to(ROOT_DIR).as_posix()
            region = r_info["region_str"]
            
            print(f"\n[CloudPilot] Generating {workload_id} (region={region}, samples={s_count})...")
            
            extract_cmd = ["bcftools", "view", "-r", region]
            s_file = sample_files[s_key]
            if s_file:
                extract_cmd.extend(["-S", s_file])
            extract_cmd.extend([rel_raw, "-Oz", "-o", rel_out])
            
            run_cmd(extract_cmd)
            
            # Tabix index
            index_cmd = ["tabix", "-p", "vcf", "-f", rel_out]
            run_cmd(index_cmd)
            
            # Verify actual variant count
            var_out = run_cmd(["bcftools", "view", "-H", rel_out])
            var_count = len(var_out.strip().splitlines()) if var_out.strip() else 0
            
            # Verify actual sample count
            smpl_out = run_cmd(["bcftools", "query", "-l", rel_out])
            actual_sample_count = len(smpl_out.strip().splitlines()) if smpl_out.strip() else 0
            
            file_size_bytes = out_vcf.stat().st_size
            compressed_size_mb = round(file_size_bytes / (1024 * 1024), 4)
            
            print(f"  + Workload ID: {workload_id}")
            print(f"  + Output file: {rel_out} ({compressed_size_mb * 1024:.1f} KB)")
            print(f"  + Variants:    {var_count}")
            print(f"  + Samples:     {actual_sample_count}")
            
            item = {
                "workload_id": workload_id,
                "chromosome": r_info["chromosome"],
                "region_start": r_info["start"],
                "region_end": r_info["end"],
                "region_size": r_info["size"],
                "variant_count": var_count,
                "sample_count": actual_sample_count,
                "compressed_size_mb": compressed_size_mb,
                "path": rel_out
            }
            metadata[workload_id] = item
            csv_rows.append(item)
            
            # For backward compatibility with Phase 1/early Phase 2
            if s_key == "full":
                metadata[r_key] = {
                    "name": out_filename,
                    "region": region,
                    "description": f"{r_key} region",
                    "path": rel_out,
                    "file_size_bytes": file_size_bytes,
                    "file_size_kb": round(file_size_bytes / 1024, 2),
                    "variant_count": var_count,
                    "sample_count": actual_sample_count
                }

    # Save metadata JSON
    meta_json = CHUNKS_DIR / "metadata.json"
    with open(meta_json, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"\n[CloudPilot] Metadata JSON saved to {meta_json.relative_to(ROOT_DIR)}")
    
    # Save metadata CSV
    meta_csv = CHUNKS_DIR / "metadata.csv"
    with open(meta_csv, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "workload_id", "chromosome", "region_start", "region_end",
            "region_size", "variant_count", "sample_count",
            "compressed_size_mb", "path"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"[CloudPilot] Metadata CSV saved to {meta_csv.relative_to(ROOT_DIR)}")

    # Also write legacy chunks_metadata.json for existing simulate.py calls
    chunks_meta = CHUNKS_DIR / "chunks_metadata.json"
    with open(chunks_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

if __name__ == "__main__":
    try:
        extract_chunks()
    except Exception as e:
        print(f"[CloudPilot] Error extracting chunks: {e}", file=sys.stderr)
        sys.exit(1)
