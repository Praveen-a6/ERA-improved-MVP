# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies AND Docker CLI (so Celery can spawn sandbox containers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    curl \
    gnupg \
    && curl -fsSL https://get.docker.com -o get-docker.sh \
    && sh get-docker.sh \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]