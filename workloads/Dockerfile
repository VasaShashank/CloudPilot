FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bcftools \
    tabix \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir psutil

# Build from the repository root:
# docker build -f workloads/Dockerfile -t cloudpilot-workload:latest .
# The directory is always present (via .gitkeep); real Phase-2 VCF chunks are
# intentionally local-only and can be generated under data/genomic/chunks.
COPY --chown=10001:10001 data/genomic/chunks/ /app/data/chunks/
COPY --chown=10001:10001 workloads/simulate.py .

USER 10001:10001

CMD ["python", "simulate.py"]
