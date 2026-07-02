FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    numpy \
    pandas \
    scikit-learn \
    scipy \
    statsmodels \
    xgboost \
    lightgbm \
    matplotlib

WORKDIR /app
CMD ["python", "/app/candidate.py"]