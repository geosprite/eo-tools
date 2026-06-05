# eo-tools deployment test

This guide validates an `eo-tools` package locally first, then deploys the same
container image to a k3s cluster. The current k3s control-plane node is
`10.168.162.111`; keep this as a variable because the node IP may change.

## Current scope

The deployable services in this repo are:

```text
tools/eo-tools-catalog
tools/eo-tools-raster
```

Both expose the runtime REST API on port `8000`. Catalog is mostly stateless.
Raster also needs GDAL, `eo-store` configuration, MinIO/S3 credentials, shared
pod-local temporary storage, and an aria2 sidecar for download-heavy HTTP
inputs.

Tool package discovery should use the installed Python entry point group
`geosprite.eo.tools`. The expected entry points are:

```text
catalog -> geosprite.eo.tools.catalog
raster -> geosprite.eo.tools.raster
```

When discovery is working, the catalog package currently registers these tools:

```text
bounds
systems
tiles
publish.collection
publish.item
meta.assets
match
search.msi
search.sar
```

The raster package currently registers these tools:

```text
compose
stack
```

Both are in the `raster` domain, so the typed REST routes are
`/raster/compose` and `/raster/stack`.

## 1. Local isolated Python smoke test

Run from the parent `eo` directory.

Catalog:

```powershell
cd C:\Users\songj\Documents\code\geosprite\eo
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e .\eo-tools\core -e ".\eo-tools\runtime[rest]" -e .\eo-catalog\core -e .\eo-catalog\grs -e .\eo-catalog\stac -e .\eo-tools\tools\eo-tools-catalog
```

Raster:

```powershell
cd C:\Users\songj\Documents\code\geosprite\eo
python -m venv .venv
.\.venv\Scripts\python -m pip install -U pip
.\.venv\Scripts\python -m pip install -e .\eo-io -e .\eo-raster -e ".\eo-store[s3,aria2]" -e .\eo-tools\core -e ".\eo-tools\runtime[rest,store]" -e .\eo-tools\tools\eo-tools-raster
```

Raster requires GDAL Python bindings that match the host GDAL library. If the
local Python install cannot import `osgeo.gdal`, install GDAL for the host first
and then install the matching Python wheel:

```powershell
gdal-config --version
.\.venv\Scripts\python -m pip install "GDAL==<gdal-config-version>"
```

Validate entry point discovery:

```powershell
@'
from importlib.metadata import entry_points
for ep in entry_points(group="geosprite.eo.tools"):
    print(f"{ep.name} -> {ep.value} ({ep.dist.name})")
'@ | .\.venv\Scripts\python -

.\.venv\Scripts\eo-tools list
```

Start REST using entry point discovery. Do not pass `--tool-package` for this
test, because the goal is to validate installed entry points.

Catalog:

```powershell
.\.venv\Scripts\eo-tools-rest --host 0.0.0.0 --port 8000
```

Raster with local MinIO:

```powershell
docker compose -f eo-store\deploy\local-minio\docker-compose.yml up -d
.\.venv\Scripts\eo-tools-rest --host 0.0.0.0 --port 8000 --workdir .\.work\raster --store-config .\eo-infra\store\local\store.minio.example.json
```

In another terminal:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/
curl.exe http://127.0.0.1:8000/docs
```

Expected health response:

```json
{"status":"ok"}
```

The tool listing endpoint is `/`, not `/tools`.

When the service is exposed behind a path-prefix reverse proxy, pass
`--root-path` so FastAPI generates OpenAPI and Swagger UI URLs with the external
prefix. When multiple tool services share the same external prefix, pass
`--service-path` so service-level endpoints such as docs, OpenAPI, health, and
tool listing live under the tool domain path without duplicating the domain in
typed tool routes:

```powershell
.\.venv\Scripts\eo-tools-rest --host 0.0.0.0 --port 8000 --root-path /eo-tools --service-path /catalog
.\.venv\Scripts\eo-tools-rest --host 0.0.0.0 --port 8000 --root-path /eo-tools --service-path /raster --workdir .\.work\raster --store-config .\eo-infra\store\local\store.minio.example.json
```

With this pattern, the reverse proxy strips only `/eo-tools`. For example,
external `/eo-tools/catalog/docs` reaches the catalog service as
`/catalog/docs`, and external `/eo-tools/catalog/search/msi` reaches it as the
typed tool route `/catalog/search/msi`.

## 2. Local Docker image test

Build from the parent `eo` directory so each Dockerfile can copy `eo-tools/` and
the sibling packages it needs.

Catalog:

```powershell
cd C:\Users\songj\Documents\code\geosprite\eo
docker build -t eo-tools-catalog:0.1.0 -f eo-tools\tools\eo-tools-catalog\deploy\docker\Dockerfile .
docker run --rm -p 8000:8000 eo-tools-catalog:0.1.0
```

Raster:

```powershell
cd C:\Users\songj\Documents\code\geosprite\eo
docker build -t eo-tools-raster:0.1.0 -f eo-tools\tools\eo-tools-raster\deploy\docker\Dockerfile .
docker run --rm -p 8000:8000 -v ${PWD}\eo-infra\store\local\store.minio.example.json:/store.json:ro -v ${PWD}\.work\raster:/work eo-tools-raster:0.1.0 eo-tools serve-rest --host 0.0.0.0 --port 8000 --workdir /work --store-config /store.json
```

In another terminal:

```powershell
curl.exe http://127.0.0.1:8000/health
curl.exe http://127.0.0.1:8000/
```

## 3. Deploy to k3s through a private registry

Use a private registry when the k3s cluster should pull images from your own
Docker repository hub instead of importing tar files into containerd manually.

### 3.0 Automated deployment script

The recommended repeatable path is the deployment script pair under each tool
package's `deploy/scripts/` directory.

Catalog:

```powershell
.\eo-tools\tools\eo-tools-catalog\deploy\scripts\deploy-catalog.ps1 `
  -SshHost jsong@10.168.162.111 `
  -K3sNodeIp 10.168.162.111 `
  -RegistryHost 10.168.162.111:5000 `
  -ImageTag 0.1.1
```

Raster:

```powershell
.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 `
  -SshHost jsong@10.168.162.111 `
  -K3sNodeIp 10.168.162.111 `
  -RegistryHost 10.168.162.111:5000 `
  -ImageTag 0.1.1
```

The PowerShell script builds the image, tags it for the registry, pushes it,
copies the manifest and remote script to the k3s node, then runs the remote
deployment script. The remote script pulls the image through k3s containerd,
renders the manifest with the pushed image, applies it, waits for rollout, and
checks the service health plus OpenAPI endpoint.

Use a new `-ImageTag` for every code change. Reusing the same tag can leave k3s
running a cached image.

Useful options:

```powershell
.\eo-tools\tools\eo-tools-catalog\deploy\scripts\deploy-catalog.ps1 -DryRun -ImageTag 0.1.1
.\eo-tools\tools\eo-tools-catalog\deploy\scripts\deploy-catalog.ps1 -NoBuild -ImageTag 0.1.1
.\eo-tools\tools\eo-tools-catalog\deploy\scripts\deploy-catalog.ps1 -SkipRemote -ImageTag 0.1.1
.\eo-tools\tools\eo-tools-catalog\deploy\scripts\deploy-catalog.ps1 -KeepRemoteDir -ImageTag 0.1.1

.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 -DryRun -ImageTag 0.1.1
.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 -NoBuild -ImageTag 0.1.1
.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 -SkipRemote -ImageTag 0.1.1
.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 -KeepRemoteDir -ImageTag 0.1.1
```

### 3.1 Push the image to the private registry

Set deployment variables first. Adjust `REGISTRY_HOST` to the real registry
endpoint once it is installed.

PowerShell:

```powershell
$K3S_NODE_IP = "10.168.162.111"
$REGISTRY_HOST = "${K3S_NODE_IP}:5000"
$IMAGE_NAME = "eo-tools-catalog" # or eo-tools-raster
$IMAGE_TAG = "0.1.0"
$IMAGE = "${REGISTRY_HOST}/${IMAGE_NAME}:${IMAGE_TAG}"
```

On the machine where the Docker image exists:

```powershell
docker tag ${IMAGE_NAME}:${IMAGE_TAG} $IMAGE
docker push $IMAGE
```

If the registry requires login:

```powershell
docker login $REGISTRY_HOST
docker push $IMAGE
```

If `docker push` tries `https://<registry>/v2/...` and fails with `EOF` while
the registry is an HTTP registry, confirm the Docker daemon trusts it as an
insecure registry:

```powershell
curl.exe http://10.168.162.111:5000/v2/
docker info | Select-String -Pattern "Insecure Registries","10.168.162.111" -Context 0,5
```

Docker Desktop should include this in `C:\Users\<user>\.docker\daemon.json`:

```json
{
  "insecure-registries": ["10.168.162.111:5000"]
}
```

Restart Docker Desktop after changing daemon settings, then retry:

```powershell
docker push $IMAGE
```

### 3.2 Make k3s trust the private registry

If the registry uses a public TLS certificate and does not require special
containerd configuration, skip this step.

For an insecure HTTP registry or a self-signed registry, configure every k3s
node that may run the workload. On a single-node cluster, do this on
`10.168.162.111`.

```bash
sudo mkdir -p /etc/rancher/k3s
sudo tee /etc/rancher/k3s/registries.yaml >/dev/null <<'YAML'
mirrors:
  "10.168.162.111:5000":
    endpoint:
      - "http://10.168.162.111:5000"
YAML

sudo systemctl restart k3s
```

Verify the node can pull the image:

```bash
sudo k3s crictl pull 10.168.162.111:5000/eo-tools-catalog:0.1.0
sudo k3s crictl pull 10.168.162.111:5000/eo-tools-raster:0.1.0
```

### 3.3 Apply the k8s manifest

Copy the manifest to the node if you run `kubectl` there:

```powershell
scp eo-tools\tools\eo-tools-catalog\deploy\k8s\eo-tools-catalog.yaml <user>@10.168.162.111:/tmp/
scp eo-tools\tools\eo-tools-raster\deploy\k8s\eo-tools-raster.yaml <user>@10.168.162.111:/tmp/
```

On the k3s node, render a temporary manifest with the registry image.

Catalog:

```bash
K3S_NODE_IP=10.168.162.111
REGISTRY_HOST="${K3S_NODE_IP}:5000"
IMAGE="${REGISTRY_HOST}/eo-tools-catalog:0.1.0"

sed "s|image: eo-tools-catalog:0.1.0|image: ${IMAGE}|g" \
  /tmp/eo-tools-catalog.yaml > /tmp/eo-tools-catalog.rendered.yaml

sudo k3s kubectl apply -f /tmp/eo-tools-catalog.rendered.yaml
sudo k3s kubectl -n eo-tools rollout status deploy/eo-tools-catalog-rest
sudo k3s kubectl -n eo-tools get pods,svc,ingress
```

Raster:

```bash
K3S_NODE_IP=10.168.162.111
REGISTRY_HOST="${K3S_NODE_IP}:5000"
IMAGE="${REGISTRY_HOST}/eo-tools-raster:0.1.0"

sed "s|image: eo-tools-raster:0.1.0|image: ${IMAGE}|g" \
  /tmp/eo-tools-raster.yaml > /tmp/eo-tools-raster.rendered.yaml

sudo k3s kubectl apply -f /tmp/eo-tools-raster.rendered.yaml
sudo k3s kubectl -n eo-tools rollout status deploy/eo-tools-raster-rest
sudo k3s kubectl -n eo-tools get pods,svc,ingress,pvc
```

Before using raster tools against `s3://` inputs or outputs, review the
`eo-tools-raster-store-config` Secret in the raster manifest. The committed
manifest uses the default example MinIO endpoint and example credentials from
`eo-infra/store/k3s/secret.example.yaml`. Replace them for real clusters:

```bash
sudo k3s kubectl -n eo-tools edit secret eo-tools-raster-store-config
sudo k3s kubectl -n eo-tools rollout restart deploy/eo-tools-raster-rest
```

If the registry requires authentication for pulls, create an image pull secret
before or after applying the manifest:

```bash
REGISTRY_HOST=10.168.162.111:5000

sudo k3s kubectl -n eo-tools create secret docker-registry registry-credentials \
  --docker-server="${REGISTRY_HOST}" \
  --docker-username="<username>" \
  --docker-password="<password>" \
  --docker-email="<email>" \
  --dry-run=client -o yaml | sudo k3s kubectl apply -f -

sudo k3s kubectl -n eo-tools patch deployment eo-tools-catalog-rest \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"registry-credentials"}]}}}}'

sudo k3s kubectl -n eo-tools patch deployment eo-tools-catalog-mcp \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"registry-credentials"}]}}}}'

sudo k3s kubectl -n eo-tools patch deployment eo-tools-raster-rest \
  -p '{"spec":{"template":{"spec":{"imagePullSecrets":[{"name":"registry-credentials"}]}}}}'
```

Validate through Traefik ingress:

```bash
curl http://10.168.162.111/eo-tools/catalog/health
curl http://10.168.162.111/eo-tools/catalog/
curl http://10.168.162.111/eo-tools/raster/health
curl http://10.168.162.111/eo-tools/raster/
```

OpenAPI docs should be available at:

```text
http://10.168.162.111/eo-tools/catalog/docs
http://10.168.162.111/eo-tools/raster/docs
```

### 3.4 Fallback: import image tar directly

Use this only when the private registry is not available yet.

Catalog:

```powershell
docker save eo-tools-catalog:0.1.0 -o eo-tools-catalog-0.1.0.tar
scp eo-tools-catalog-0.1.0.tar <user>@10.168.162.111:/tmp/
scp eo-tools\tools\eo-tools-catalog\deploy\k8s\eo-tools-catalog.yaml <user>@10.168.162.111:/tmp/
```

```bash
sudo k3s ctr images import /tmp/eo-tools-catalog-0.1.0.tar
sudo k3s kubectl apply -f /tmp/eo-tools-catalog.yaml
sudo k3s kubectl -n eo-tools rollout status deploy/eo-tools-catalog-rest
```

Raster:

```powershell
docker save eo-tools-raster:0.1.0 -o eo-tools-raster-0.1.0.tar
scp eo-tools-raster-0.1.0.tar <user>@10.168.162.111:/tmp/
scp eo-tools\tools\eo-tools-raster\deploy\k8s\eo-tools-raster.yaml <user>@10.168.162.111:/tmp/
```

```bash
sudo k3s ctr images import /tmp/eo-tools-raster-0.1.0.tar
sudo k3s kubectl apply -f /tmp/eo-tools-raster.yaml
sudo k3s kubectl -n eo-tools rollout status deploy/eo-tools-raster-rest
```

## 4. Useful k3s diagnostics

```bash
sudo k3s kubectl -n eo-tools describe pod -l app.kubernetes.io/name=eo-tools-catalog-rest
sudo k3s kubectl -n eo-tools logs deploy/eo-tools-catalog-rest
sudo k3s kubectl -n eo-tools describe pod -l app.kubernetes.io/name=eo-tools-raster-rest
sudo k3s kubectl -n eo-tools logs deploy/eo-tools-raster-rest -c rest
sudo k3s kubectl -n eo-tools logs deploy/eo-tools-raster-rest -c aria2
sudo k3s kubectl -n eo-tools get events --sort-by=.lastTimestamp
```

Cleanup:

```bash
sudo k3s kubectl delete -f /tmp/eo-tools-catalog.rendered.yaml
sudo k3s kubectl delete -f /tmp/eo-tools-raster.rendered.yaml
```
