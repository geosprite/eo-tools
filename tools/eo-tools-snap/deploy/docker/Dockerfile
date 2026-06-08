FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ARG SNAP_INSTALLER_URL=https://download.esa.int/step/snap/13.0/installers/esa-snap_sentinel_linux-13.0.0.sh

ENV SNAP_HOME=/opt/snap \
    PATH="/opt/venv/bin:/opt/snap/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /src

# Build with the parent `eo/` directory as context so sibling packages are visible:
# docker build -f eo-tools/tools/eo-tools-snap/deploy/docker/Dockerfile .
COPY eo-tools ./eo-tools
COPY eo-io ./eo-io
COPY eo-raster ./eo-raster
COPY eo-store ./eo-store

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        aria2 \
        bash \
        build-essential \
        ca-certificates \
        coreutils \
        curl \
        fontconfig \
        gdal-bin \
        libfreetype6 \
        libgdal32 \
        libx11-6 \
        libxext6 \
        libxi6 \
        libxrender1 \
        libxtst6 \
        libgdal-dev \
        python3 \
        python3-dev \
        python3-gdal \
        python3-venv \
        wget \
    && rm -rf /var/lib/apt/lists/*

RUN uv venv --python /usr/bin/python3 --system-site-packages /opt/venv

RUN uv pip install --no-config --no-sources --no-cache \
        "numpy<2" \
        "GDAL==$(gdal-config --version)" \
        "./eo-store[s3,aria2]" \
        ./eo-io \
        ./eo-raster \
        ./eo-tools/core \
        "./eo-tools/runtime[all]"

RUN uv pip install --no-config --no-sources --no-cache --no-deps \
        ./eo-tools/tools/eo-tools-snap

RUN wget -q -O /tmp/esa-snap.sh "$SNAP_INSTALLER_URL" \
    && bash /tmp/esa-snap.sh -q -dir "$SNAP_HOME" \
    && rm /tmp/esa-snap.sh \
    && uv pip install --no-config --no-cache esa-snappy \
    && cd "$SNAP_HOME/bin" \
    && timeout 600 ./snappy-conf /opt/venv/bin/python || true \
    && python -c "import esa_snappy; from esa_snappy import ProductIO"

RUN useradd --system --uid 10001 --create-home eo \
    && mkdir -p /work/runtime /work/aria2 \
    && chown -R eo:eo /work /home/eo

USER eo
WORKDIR /work

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"

CMD ["eo-tools", "serve-rest", "--host", "0.0.0.0", "--port", "8000", "--service-path", "/snap", "--workdir", "/work/runtime", "--store-config", "/etc/eo-tools/store/store.json"]
