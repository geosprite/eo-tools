# eo-tools-snap deployment

This directory deploys `eo-tools-snap` with ESA SNAP 13.0.0 and an Aria2 RPC
companion used by the `eo-store` `aria2_http` backend.

The Docker image installs SNAP from:

```text
https://download.esa.int/step/snap/13.0/installers/esa-snap_sentinel_linux-13.0.0.sh
```

## Local Docker

From the repository root:

```powershell
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap-local.ps1
```

Useful options:

```powershell
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap-local.ps1 -ImageTag dev -Port 8001
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap-local.ps1 -Down
```

Expected local URLs:

```text
http://127.0.0.1:8000/snap/health
http://127.0.0.1:8000/snap/docs
```

## k3s on 10.168.162.111

From the repository root:

```powershell
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap.ps1 `
  -SshHost jsong@10.168.162.111 `
  -K3sNodeIp 10.168.162.111 `
  -RegistryHost 10.168.162.111:5000
```

The script builds the image, pushes it to the registry, copies the rendered
manifest and remote script to the k3s node, applies the manifest with
`sudo k3s kubectl`, and validates the REST endpoints through Traefik.

Useful options:

```powershell
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap.ps1 -DryRun
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap.ps1 -NoBuild -ImageTag <existing-tag>
.\eo-tools\tools\eo-tools-snap\deploy\scripts\deploy-snap.ps1 -NoPush -SkipRemote
```

Expected k3s URLs:

```text
http://10.168.162.111/eo-tools/snap/health
http://10.168.162.111/eo-tools/snap/docs
```

The default k3s manifest uses `emptyDir` for `/work`. This avoids failures when
the k3s `rancher.io/local-path` provisioner is slow or unhealthy. If persistent
workspace storage is required and the provisioner is healthy, apply
`k8s/eo-tools-snap-pvc-work.patch.yaml` after the base manifest or adapt it to
your cluster storage class.

## Store and Aria2

The REST container and Aria2 RPC container share `/work`. Aria2 writes staged
downloads to `/work/aria2`, and `eo-store` is configured to connect to Aria2 at
`127.0.0.1:6800` in k3s or `aria2:6800` in local Docker Compose.

Aria2 RPC is intentionally not exposed outside the workload.
