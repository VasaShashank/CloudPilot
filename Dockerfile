FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=10001:10001 . .

EXPOSE 8000

USER 10001:10001

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]