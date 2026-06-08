#!/usr/bin/env bash
set -euo pipefail

IMAGE=""
NODE_IP=""
MANIFEST=""
NAMESPACE="eo-tools"
REST_DEPLOYMENT="eo-tools-snap-rest"
RENDERED_MANIFEST=""

usage() {
  cat <<'EOF'
Usage:
  deploy-snap-remote.sh --image IMAGE --node-ip NODE_IP --manifest MANIFEST [--namespace NAMESPACE]

Example:
  deploy-snap-remote.sh \
    --image 10.168.162.111:5000/eo-tools-snap:20260609120000 \
    --node-ip 10.168.162.111 \
    --manifest /tmp/eo-tools-snap-deploy/eo-tools-snap.yaml
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --image)
      IMAGE="$2"
      shift 2
      ;;
    --node-ip)
      NODE_IP="$2"
      shift 2
      ;;
    --manifest)
      MANIFEST="$2"
      shift 2
      ;;
    --namespace)
      NAMESPACE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$IMAGE" || -z "$NODE_IP" || -z "$MANIFEST" ]]; then
  usage >&2
  exit 2
fi

if [[ ! -f "$MANIFEST" ]]; then
  echo "Manifest not found: $MANIFEST" >&2
  exit 1
fi

if ! command -v sudo >/dev/null 2>&1; then
  echo "sudo is required on the k3s node." >&2
  exit 1
fi

echo "Checking sudo access..."
sudo -v

if ! command -v k3s >/dev/null 2>&1; then
  echo "k3s is not in PATH for user $(id -un)." >&2
  echo "If k3s is installed elsewhere, add it to PATH or create a symlink visible to this user." >&2
  exit 1
fi

if ! sudo k3s kubectl version --client; then
  echo "sudo k3s kubectl is not available or failed." >&2
  exit 1
fi

if ! sudo k3s crictl pull "$IMAGE"; then
  echo "Image pull failed from k3s containerd: $IMAGE" >&2
  exit 1
fi

RENDERED_MANIFEST="$(dirname "$MANIFEST")/eo-tools-snap.rendered.yaml"

awk -v image="$IMAGE" '
  /^[[:space:]]*image:[[:space:]]*/ && $0 ~ /(^|\/)eo-tools-snap:/ {
    sub(/image:[[:space:]].*$/, "image: " image)
  }
  { print }
' "$MANIFEST" > "$RENDERED_MANIFEST"

if ! grep -Fq "image: ${IMAGE}" "$RENDERED_MANIFEST"; then
  echo "Rendered manifest does not contain expected image: ${IMAGE}" >&2
  exit 1
fi

DEPLOYMENT_EXISTS=0
if sudo k3s kubectl -n "$NAMESPACE" get deploy "$REST_DEPLOYMENT" >/dev/null 2>&1; then
  DEPLOYMENT_EXISTS=1
fi

sudo k3s kubectl apply -f "$RENDERED_MANIFEST"

if [[ "$DEPLOYMENT_EXISTS" == "1" ]]; then
  sudo k3s kubectl -n "$NAMESPACE" rollout restart "deploy/${REST_DEPLOYMENT}"
fi

sudo k3s kubectl -n "$NAMESPACE" rollout status "deploy/${REST_DEPLOYMENT}"
sudo k3s kubectl -n "$NAMESPACE" get pods,svc,ingress,pvc

echo ""
echo "Validating REST endpoints through Traefik:"
curl -fsS "http://${NODE_IP}/eo-tools/snap/health"
echo ""
curl -fsS "http://${NODE_IP}/eo-tools/snap/" >/dev/null
echo "Tool list OK"
if curl -fsS --max-time 60 "http://${NODE_IP}/eo-tools/snap/openapi.json" >/dev/null; then
  echo "OpenAPI OK"
else
  echo "OpenAPI validation skipped after timeout or non-2xx response." >&2
  echo "Deployment is healthy; check /eo-tools/snap/docs manually if needed." >&2
fi
echo ""
echo "Expected browser URL:"
echo "  http://${NODE_IP}/eo-tools/snap/docs"
