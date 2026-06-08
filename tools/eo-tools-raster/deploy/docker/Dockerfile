FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /src

# Build with the parent `eo/` directory as context so sibling repos are visible:
# docker build -f eo-tools/tools/eo-tools-raster/deploy/docker/Dockerfile .
COPY eo-tools ./eo-tools
COPY eo-io ./eo-io
COPY eo-raster ./eo-raster
COPY eo-store ./eo-store

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gdal-bin \
        python3 \
        python3-gdal \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN uv venv --python /usr/bin/python3 --system-site-packages /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install --no-config --no-sources --no-cache \
    "numpy<2" \
    shapely \
    "./eo-store[s3,aria2]" \
    ./eo-tools/core \
    "./eo-tools/runtime[all]"

RUN uv pip install --no-config --no-sources --no-cache --no-deps \
    ./eo-io \
    ./eo-raster \
    ./eo-tools/tools/eo-tools-raster

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        aria2 \
        gdal-bin \
        libgdal32 \
        python3 \
        python3-gdal \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --system --uid 10001 --create-home eo \
    && mkdir -p /work/runtime /work/aria2 \
    && chown -R eo:eo /work

COPY --from=builder /opt/venv /opt/venv

USER eo
WORKDIR /work

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"

CMD ["eo-tools", "serve-rest", "--host", "0.0.0.0", "--port", "8000", "--workdir", "/work"]
