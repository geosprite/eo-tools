FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /src

# Build with the parent `eo/` directory as context so sibling repos are visible:
# docker build -f eo-tools/tools/eo-tools-catalog/deploy/docker/Dockerfile .
COPY eo-tools ./eo-tools
COPY eo-catalog ./eo-catalog

RUN uv venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

RUN uv pip install --no-config --no-sources --no-cache \
    ./eo-catalog/core \
    ./eo-catalog/grs \
    ./eo-catalog/stac \
    ./eo-tools/core \
    "./eo-tools/runtime[all]"

RUN uv pip install --no-config --no-sources --no-cache --no-deps \
    ./eo-tools/tools/eo-tools-catalog

FROM python:3.12-slim-bookworm

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /opt/venv /opt/venv

RUN useradd --system --uid 10001 --create-home eo
USER eo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read()"

CMD ["eo-tools", "serve-rest", "--host", "0.0.0.0", "--port", "8000"]
