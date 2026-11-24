FROM node:22-bookworm-slim

# Install Python + basics
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project
COPY requirements.txt .
COPY bot.py .
COPY networks.json .
COPY setup.sh .

# Python deps
RUN python3 -m venv /app/.venv \
    && /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

# Pre-warm the FLOP CLI
RUN npx --yes @flop-labs/cli@0.7.0 --version || true

# Create runtime dirs
RUN mkdir -p /app/keystore /app/state /app/logs

ENV PATH="/app/.venv/bin:$PATH"
ENV FLOP_NETWORK=testnet
ENV MAX_FLOP_PER_SESSION=0.5
ENV MAX_SESSIONS_PER_DAY=40
ENV MIN_BALANCE_TO_SPEND=0.2
ENV LOOP_SLEEP=90

VOLUME ["/app/keystore", "/app/state", "/app/logs"]

CMD ["python3", "bot.py"]
