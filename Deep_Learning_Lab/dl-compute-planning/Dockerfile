FROM python:3.11.9-slim-bookworm

# No OMP_NUM_THREADS limit here: the CPU benchmark should use every core the machine has
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/tmp/matplotlib

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY config/ ./config/
COPY src/ ./src/

CMD ["python", "-m", "src.benchmark", "--help"]
