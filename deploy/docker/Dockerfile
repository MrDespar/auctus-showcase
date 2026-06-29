FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    inotify-tools \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

VOLUME ["/workspace/data", "/workspace/outputs", "/workspace/logs"]

ENTRYPOINT ["bash", "deploy/scripts/watch_inputs.sh"]
