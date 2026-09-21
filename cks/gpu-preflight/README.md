# GPU preflight check

Use this example to verify that a CKS namespace can schedule a one-GPU workload, expose NVIDIA devices inside the container, and optionally mount a PersistentVolumeClaim before deploying a larger model server, training job, renderer, or notebook.

This check is intentionally small. It helps catch common setup issues early, before users spend time debugging a larger GPU deployment.

## What this checks

- The namespace can schedule a pod that requests `nvidia.com/gpu: "1"`.
- NVIDIA device files are visible inside the container.
- `nvidia-smi` can communicate with the GPU driver.
- Optional persistent storage mounts at `/workspace`.

## Quick start

```bash
kubectl create namespace gpu-preflight
kubectl apply -n gpu-preflight -f pvc.yaml
kubectl apply -n gpu-preflight -f job.yaml
kubectl logs -n gpu-preflight job/gpu-preflight
kubectl delete namespace gpu-preflight
```

If you do not want to test storage, skip `pvc.yaml` and remove the `volumes` and `volumeMounts` sections from `job.yaml`.

## Customize for your cluster

Before running this in a production environment, review:

- `resources.requests` and `resources.limits` for CPU, memory, and GPU count.
- `storageClassName` in `pvc.yaml`, if your cluster requires an explicit storage class.
- Optional node selectors, tolerations, or affinity rules used by your organization.
- The CUDA image tag if your workload requires a specific CUDA major version.

## Expected output

A successful run prints the pod hostname, date, NVIDIA device files, `nvidia-smi` output, CUDA version information when present, and filesystem details for `/workspace`.
