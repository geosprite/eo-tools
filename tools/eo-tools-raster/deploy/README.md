# eo-tools-raster deployment

Local Docker assets live under `docker/`:

```powershell
docker compose -f .\eo-tools\tools\eo-tools-raster\deploy\docker\docker-compose.yaml up --build
```

The default k3s manifest uses `emptyDir` for `/work`. This matches the
`eo-tools-snap` deployment and avoids rollout failures when the k3s
`rancher.io/local-path` provisioner is slow or unhealthy.

Deploy to `10.168.162.111` from the repository root:

```powershell
.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 `
  -SshHost jsong@10.168.162.111 `
  -K3sNodeIp 10.168.162.111 `
  -RegistryHost 10.168.162.111:5000
```

To reuse an already pushed image and only apply the updated manifest:

```powershell
.\eo-tools\tools\eo-tools-raster\deploy\scripts\deploy-raster.ps1 `
  -SshHost jsong@10.168.162.111 `
  -K3sNodeIp 10.168.162.111 `
  -RegistryHost 10.168.162.111:5000 `
  -ImageTag <existing-tag> `
  -NoBuild `
  -NoPush
```

If persistent workspace storage is required and the provisioner is healthy,
apply `k8s/eo-tools-raster-pvc-work.patch.yaml` after the base manifest or adapt
it to your cluster storage class.
