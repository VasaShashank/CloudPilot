FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    bcftools \
    tabix \
    procps \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir psutil

COPY data/chunks /app/data/chunks
COPY simulate.py .
CMD ["python", "simulate.py"]
