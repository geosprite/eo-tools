# =============================================================================
# Stage 1: builder - install runtime deps and Nuitka build tools
# =============================================================================
# Build with the parent eo/ directory as context so sibling repos are visible:
#   docker build -f eo-tools/tools/eo-tools-raster/deploy/docker/Dockerfile .
#
# To add a new tool plugin:
#   1. Declare an entry point in its pyproject.toml:
#        [project.entry-points."geosprite.eo.tools"]
#        plugin_name = "geosprite.eo.tools.plugin_name"
#   2. Add the package path to the plugin uv pip install command below.
# Plugin packages should expose a geosprite.eo.tools entry point. Packages may
# point at a build_registry callable to avoid filesystem-dependent discovery.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /src

COPY eo-tools  ./eo-tools
COPY eo-io     ./eo-io
COPY eo-raster ./eo-raster
COPY eo-store  ./eo-store

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        patchelf \
        gdal-bin \
        python3 \
        python3-dev \
        python3-gdal \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

RUN uv venv --python /usr/bin/python3 --system-site-packages /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install --no-config --no-sources --no-cache \
        "numpy<2" \
        shapely \
        nuitka \
        ordered-set \
        zstandard \
        "./eo-store[s3,aria2]" \
        ./eo-tools/core \
        "./eo-tools/runtime[all]"

RUN uv pip install --no-config --no-sources --no-cache --no-deps \
        ./eo-io \
        ./eo-raster \
        ./eo-tools/tools/eo-tools-raster

# =============================================================================
# Stage 2: compiler - compile installed packages, then remove sources
# =============================================================================
FROM builder AS compiler

WORKDIR /compile
ENV NUITKA_CACHE_DIR=/tmp/nuitka-cache

RUN python3 -c \
    "import pathlib, site; pathlib.Path('/compile/SP').write_text(site.getsitepackages()[0])"

# Compile geosprite.eo.io.
RUN SP=$(cat /compile/SP) && \
    python3 -m nuitka \
        --module \
        --include-package=geosprite.eo.io \
        --remove-output \
        --no-pyi-file \
        --output-dir="$SP/geosprite/eo" \
        "$SP/geosprite/eo/io" \
    && find "$SP/geosprite/eo/io" -name "*.py" -delete \
    && find "$SP/geosprite/eo/io" -name "*.pyc" -delete \
    && find "$SP/geosprite/eo/io" -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Compile geosprite.eo.raster.
RUN SP=$(cat /compile/SP) && \
    python3 -m nuitka \
        --module \
        --include-package=geosprite.eo.raster \
        --remove-output \
        --no-pyi-file \
        --output-dir="$SP/geosprite/eo" \
        "$SP/geosprite/eo/raster" \
    && find "$SP/geosprite/eo/raster" -name "*.py" -delete \
    && find "$SP/geosprite/eo/raster" -name "*.pyc" -delete \
    && find "$SP/geosprite/eo/raster" -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Compile geosprite.eo.store.
RUN SP=$(cat /compile/SP) && \
    python3 -m nuitka \
        --module \
        --include-package=geosprite.eo.store \
        --remove-output \
        --no-pyi-file \
        --output-dir="$SP/geosprite/eo" \
        "$SP/geosprite/eo/store" \
    && find "$SP/geosprite/eo/store" -name "*.py" -delete \
    && find "$SP/geosprite/eo/store" -name "*.pyc" -delete \
    && find "$SP/geosprite/eo/store" -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Compile geosprite.eo.tools as one unit so core, runtime, and raster can
# import each other inside the same .so.
RUN SP=$(cat /compile/SP) && \
    python3 -m nuitka \
        --module \
        --include-package=geosprite.eo.tools \
        --remove-output \
        --no-pyi-file \
        --output-dir="$SP/geosprite/eo" \
        "$SP/geosprite/eo/tools" \
    && find "$SP/geosprite/eo/tools" -name "*.py" -delete \
    && find "$SP/geosprite/eo/tools" -name "*.pyc" -delete \
    && find "$SP/geosprite/eo/tools" -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Final source sweep for protected packages.
RUN SP=$(cat /compile/SP) && \
    find "$SP/geosprite" -name "*.py" -delete && \
    find "$SP/geosprite" -name "*.pyc" -delete && \
    find "$SP/geosprite" -name "__pycache__" -exec rm -rf {} + 2>/dev/null

RUN pip uninstall -y nuitka ordered-set zstandard 2>/dev/null || true && \
    rm -rf /tmp/nuitka-cache /compile

# =============================================================================
# Stage 3: runtime - lean final image with no geosprite .py sources
# =============================================================================
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

COPY --from=compiler /opt/venv /opt/venv

USER eo
WORKDIR /work

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"

CMD ["eo-tools", "serve-rest", "--host", "0.0.0.0", "--port", "8000", "--workdir", "/work"]
