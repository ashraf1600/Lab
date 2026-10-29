FROM python:3.11.9-slim-bookworm

# DVC works on a Git repository, so the image needs git
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# The project (code, data, .git, .dvc) is mounted at /work at run time, not copied
WORKDIR /work
CMD ["dvc", "--version"]
