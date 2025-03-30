FROM node:10.17.0-alpine AS npm
WORKDIR /code
COPY ./static/package*.json /code/static/
RUN cd /code/static && npm ci

FROM ubuntu:22.04

ARG UV_VERSION="0.5.21"

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /code

# Copy dependency files
COPY pyproject.toml uv.lock .python-version ./

# Install deps and dependencies for uname
RUN apt-get update \
    && apt-get install -y curl netcat-traditional gcc python3-dev gnupg git libre2-dev build-essential pkg-config cmake ninja-build bash clang coreutils \
    && ARCH=$(uname -m) && \
    case "$ARCH" in \
    "x86_64") UV_ARCH="x86_64-unknown-linux-gnu" ;; \
    "aarch64") UV_ARCH="aarch64-unknown-linux-gnu" ;; \
    *) echo "Unsupported architecture: $ARCH" && exit 1 ;; \
    esac && \
    UV_URL="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-${UV_ARCH}.tar.gz" && \
    echo "Downloading UV from $UV_URL" && \
    curl -sSL "$UV_URL" > uv.tar.gz && \
    tar xf uv.tar.gz -C /tmp/ && \
    mv /tmp/uv-*/uv /usr/bin/uv && \
    mv /tmp/uv-*/uvx /usr/bin/uvx && \
    rm -rf /tmp/uv* uv.tar.gz

# Install Python dependencies
RUN uv python install `cat .python-version` \
    && export CMAKE_POLICY_VERSION_MINIMUM=3.5 \
    && uv sync --locked \
    && apt-get autoremove -y \
    && apt-get purge -y curl netcat-traditional build-essential pkg-config cmake ninja-build python3-dev clang \
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy code
COPY . .

# Copy npm packages
COPY --from=npm /code /code

ENV PATH="/code/.venv/bin:$PATH"
EXPOSE 7777

CMD ["gunicorn", "wsgi:app", "-b", "0.0.0.0:7777", "-w", "2", "--timeout", "15"]
