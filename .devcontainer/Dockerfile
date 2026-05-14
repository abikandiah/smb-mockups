FROM mcr.microsoft.com/devcontainers/base:ubuntu-22.04

# 1. Install system requirements & Node.js setup in one clean layer
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    curl \
    samba-client \
    gettext-base \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Gemini CLI globally as root
RUN npm install -g @google/gemini-cli

# 3. Install Claude CLI globally or for all users
# Note: Ensure the URL you are using is valid; alternatively, if Claude CLI is on npm:
# RUN npm install -g @anthropic-ai/claude-cli 
# Using your original curl method but forcing it to install safely as root if supported:
RUN curl -fsSL https://claude.ai/install.sh | bash -s -- -y || true

# (Optional) Ensure global node_modules and bins are in the default PATH
ENV PATH="/usr/local/bin:/usr/bin:/bin:${PATH}"