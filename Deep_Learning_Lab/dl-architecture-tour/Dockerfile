FROM python:3.11.9-slim-bookworm

# Determinism-related environment (must exist before Python starts)
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=42 \
    CUBLAS_WORKSPACE_CONFIG=:4096:8 \
    OMP_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ ./src/

CMD ["python", "-m", "src.train", "--help"]
