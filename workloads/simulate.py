import os
import sys
import time
import random
import hashlib

def main():
    stage_name = os.environ.get("STAGE_NAME")
    stage_type = os.environ.get("STAGE_TYPE", "unknown")
    fail_stage = os.environ.get("FAIL_STAGE", "false").lower() == "true"

    if not stage_name:
        print("[CloudPilot] Error: STAGE_NAME environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    print(f"[CloudPilot] {stage_name} ({stage_type}) started")

    if fail_stage:
        print(f"[CloudPilot] Error: {stage_name} failed intentionally (FAIL_STAGE=true)", file=sys.stderr)
        sys.exit(1)

    sleep_duration = random.uniform(5.0, 15.0)
    
    time.sleep(sleep_duration / 2)
    print(f"[CloudPilot] {stage_name} processing...")
    
    # Simulate computation
    data = os.urandom(1024 * 1024)
    hashlib.sha256(data).hexdigest()
    
    time.sleep(sleep_duration / 2)

    # Print result summary based on type
    if stage_type == "alignment":
        print(f"[CloudPilot] Processed {random.randint(1000, 5000)} reads")
    elif stage_type == "quality_control":
        print(f"[CloudPilot] Quality score: {random.uniform(90.0, 99.9):.1f}%")
    elif stage_type == "preprocessing":
        print(f"[CloudPilot] Filtered {random.randint(50, 500)} invalid entries")
    elif stage_type == "analysis":
        print(f"[CloudPilot] Identified {random.randint(5, 50)} variants")
    elif stage_type == "feature_extraction":
        print(f"[CloudPilot] Extracted {random.randint(100, 1000)} features from {random.randint(500, 2000)} samples")
    else:
        print(f"[CloudPilot] Processed workload data successfully")

    print(f"[CloudPilot] {stage_name} ({stage_type}) completed successfully")
    sys.exit(0)

if __name__ == "__main__":
    main()
