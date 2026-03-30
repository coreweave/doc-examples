"""Hello world for NIMS on CKS — E2E Test Notebook

Marimo notebook that tests the complete workflow for deploying and querying
a NVIDIA NIM (NVIDIA Inference Microservice) on CoreWeave Kubernetes Service:
  1. Verify kubectl access and GPU node availability
  2. Create NGC credentials secret
  3. Deploy a NIM as a Deployment + Service
  4. Wait for the NIM pod to become ready
  5. Query the NIM inference endpoint
  6. Clean up all resources

This notebook is the source of truth for the Hello World for NIMS on CKS tutorial.
Cells tagged with @tested-docs markers are extracted and injected into the
published documentation.

Run:
  e2e-test-docs run tests/hello-world-for-nims-on-cks/hello_world_for_nims_on_cks.py
"""

import marimo as mo

app = mo.App()


# --------------------------------------------------------------------------- #
# Metadata
# --------------------------------------------------------------------------- #
@app.cell
def metadata():
    # @tested-docs: schema-version 1.0
    # @tested-docs: test-id hello-world-for-nims-on-cks
    # @tested-docs: timeout 30m
    # @tested-docs: doc-url https://docs.coreweave.com/products/cks/tutorials/hello-world-for-nims-on-cks/index
    mo.md(
        """
        # Hello World for NIMS on CKS — E2E Test

        Tests the complete workflow:
        kubectl access → NGC secret → NIM deployment → inference query → cleanup
        """
    )


# --------------------------------------------------------------------------- #
# Prerequisites
# --------------------------------------------------------------------------- #
@app.cell
def prerequisites():
    # @tested-docs: prereqs
    import json
    import os
    import re
    import textwrap
    import time
    from pathlib import Path

    from tested_docs.contexts import SSHContext

    # Reuse SLURM_LOGIN_HOST / SLURM_USER for the SSH hop to a kubectl-enabled host.
    # The runner's env resolver already knows how to prompt for these.
    SLURM_LOGIN_HOST = os.environ["SLURM_LOGIN_HOST"]
    SLURM_USER = os.environ["SLURM_USER"]
    SSH_KEY_PATH = os.path.expanduser(
        os.environ.get("SSH_KEY_PATH", "~/.ssh/id_ed25519")
    )
    NGC_API_KEY = os.environ["NGC_API_KEY"]
    KUBECONFIG_PATH = os.path.expanduser(
        os.environ.get("KUBECONFIG_PATH", "~/CWKubeconfig_docs-work")
    )

    NAMESPACE = os.environ.get("CKS_NAMESPACE", "default")
    NIM_MODEL = os.environ.get("NIM_MODEL", "meta/llama3-8b-instruct")
    NIM_IMAGE = os.environ.get(
        "NIM_IMAGE", "nvcr.io/nim/meta/llama3-8b-instruct:1.0.0"
    )
    NIM_NAME = "nim-hello-world"
    TEST_DIR = Path(__file__).parent

    # Fast-fail prereq checks
    assert SLURM_LOGIN_HOST, "SLURM_LOGIN_HOST must be set"
    assert SLURM_USER, "SLURM_USER must be set"
    assert Path(SSH_KEY_PATH).exists(), (
        f"SSH key not found: {SSH_KEY_PATH}"
    )
    assert NGC_API_KEY, "NGC_API_KEY must be set"
    assert Path(KUBECONFIG_PATH).exists(), (
        f"Kubeconfig not found: {KUBECONFIG_PATH}"
    )

    return (
        SLURM_LOGIN_HOST, SLURM_USER, SSH_KEY_PATH, NGC_API_KEY,
        KUBECONFIG_PATH,
        NAMESPACE, NIM_MODEL, NIM_IMAGE, NIM_NAME, TEST_DIR,
        json, os, re, textwrap, time, Path, SSHContext,
    )


# --------------------------------------------------------------------------- #
# Connect to CKS host
# --------------------------------------------------------------------------- #
@app.cell
def connect(SLURM_LOGIN_HOST, SLURM_USER, SSH_KEY_PATH, KUBECONFIG_PATH, SSHContext):
    # @tested-docs: snippet ssh-connect
    # @tested-docs: doc-page hello-world-for-nims-on-cks/1-prerequisites
    login = SSHContext(
        host=SLURM_LOGIN_HOST,
        user=SLURM_USER,
        key_path=SSH_KEY_PATH,
    )
    result = login.run("echo 'Connected successfully'")
    assert result.exit_code == 0, f"SSH connection failed: {result.stderr}"

    # Upload kubeconfig so kubectl can reach the CKS cluster
    login.run("mkdir -p ~/.kube")
    login.upload(KUBECONFIG_PATH, "~/.kube/config")
    result = login.run("chmod 600 ~/.kube/config")
    assert result.exit_code == 0

    mo.md(f"Connected to **{SLURM_LOGIN_HOST}** as `{SLURM_USER}` — kubeconfig uploaded")
    return (login,)


# --------------------------------------------------------------------------- #
# Verify kubectl access
# --------------------------------------------------------------------------- #
@app.cell
def verify_kubectl(login, NAMESPACE):
    # @tested-docs: snippet verify-kubectl
    # @tested-docs: doc-page hello-world-for-nims-on-cks/1-prerequisites
    result = login.run(f"kubectl get nodes -o wide --no-headers | head -5")
    assert result.exit_code == 0, f"kubectl failed: {result.stderr}"
    assert result.stdout.strip(), "No nodes returned — check kubeconfig"
    mo.md(f"**Cluster nodes:**\n```\n{result.stdout.strip()}\n```")


@app.cell
def verify_gpu_nodes(login):
    # @tested-docs: snippet verify-gpu-nodes
    # @tested-docs: doc-page hello-world-for-nims-on-cks/1-prerequisites
    result = login.run(
        "kubectl get nodes "
        "-o custom-columns=NAME:.metadata.name,GPU:.status.capacity.'nvidia\\.com/gpu',STATUS:.status.conditions[-1].type "
        "--no-headers | head -5"
    )
    assert result.exit_code == 0, f"GPU node check failed: {result.stderr}"
    assert result.stdout.strip(), "No GPU nodes found in cluster"
    mo.md(f"**GPU nodes available:**\n```\n{result.stdout.strip()}\n```")


# --------------------------------------------------------------------------- #
# Create NGC credentials secret
# --------------------------------------------------------------------------- #
@app.cell
def create_ngc_secret(login, NGC_API_KEY, NAMESPACE):
    # @tested-docs: snippet create-ngc-secret
    # @tested-docs: doc-page hello-world-for-nims-on-cks/1-prerequisites
    # Delete existing secret if present (idempotent)
    login.run(
        f"kubectl delete secret ngc-credentials -n {NAMESPACE} "
        "--ignore-not-found"
    )
    result = login.run(
        f"kubectl create secret docker-registry ngc-credentials "
        f"-n {NAMESPACE} "
        f"--docker-server=nvcr.io "
        f"--docker-username='$oauthtoken' "
        f"--docker-password='{NGC_API_KEY}'"
    )
    assert result.exit_code == 0, f"Secret creation failed: {result.stderr}"
    mo.md("NGC credentials secret created")

    ngc_creds_ready = True
    return (ngc_creds_ready,)


# --------------------------------------------------------------------------- #
# Create NGC API key secret (for NIM runtime)
# --------------------------------------------------------------------------- #
@app.cell
def create_ngc_api_secret(login, NGC_API_KEY, NAMESPACE, ngc_creds_ready):
    # @tested-docs: snippet create-ngc-api-secret
    # @tested-docs: doc-page hello-world-for-nims-on-cks/2-deploy-nim
    login.run(
        f"kubectl delete secret ngc-api-key -n {NAMESPACE} "
        "--ignore-not-found"
    )
    result = login.run(
        f"kubectl create secret generic ngc-api-key "
        f"-n {NAMESPACE} "
        f"--from-literal=NGC_API_KEY='{NGC_API_KEY}'"
    )
    assert result.exit_code == 0, f"API key secret creation failed: {result.stderr}"
    mo.md("NGC API key secret created")

    ngc_api_ready = True
    return (ngc_api_ready,)


# --------------------------------------------------------------------------- #
# Deploy the NIM
# --------------------------------------------------------------------------- #
@app.cell
def deploy_nim(login, NAMESPACE, NIM_NAME, NIM_IMAGE, textwrap, ngc_api_ready):
    # @tested-docs: snippet deploy-nim
    # @tested-docs: doc-page hello-world-for-nims-on-cks/2-deploy-nim
    nim_yaml = textwrap.dedent(f"""\
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: {NIM_NAME}
      namespace: {NAMESPACE}
      labels:
        app: {NIM_NAME}
    spec:
      replicas: 1
      selector:
        matchLabels:
          app: {NIM_NAME}
      template:
        metadata:
          labels:
            app: {NIM_NAME}
        spec:
          nodeSelector:
            gpu.nvidia.com/class: L40
          imagePullSecrets:
            - name: ngc-credentials
          containers:
            - name: nim
              image: {NIM_IMAGE}
              ports:
                - containerPort: 8000
                  name: http
              env:
                - name: NGC_API_KEY
                  valueFrom:
                    secretKeyRef:
                      name: ngc-api-key
                      key: NGC_API_KEY
              resources:
                limits:
                  nvidia.com/gpu: 1
                  cpu: "4"
                  memory: "32Gi"
                requests:
                  nvidia.com/gpu: 1
                  cpu: "2"
                  memory: "16Gi"
              volumeMounts:
                - name: nim-cache
                  mountPath: /opt/nim/.cache
              readinessProbe:
                httpGet:
                  path: /v1/health/ready
                  port: 8000
                initialDelaySeconds: 30
                periodSeconds: 10
              livenessProbe:
                httpGet:
                  path: /v1/health/live
                  port: 8000
                initialDelaySeconds: 300
                periodSeconds: 15
          volumes:
            - name: nim-cache
              emptyDir: {{}}
    ---
    apiVersion: v1
    kind: Service
    metadata:
      name: {NIM_NAME}
      namespace: {NAMESPACE}
    spec:
      selector:
        app: {NIM_NAME}
      ports:
        - name: http
          port: 8000
          targetPort: 8000
      type: ClusterIP
    """)

    # Write the manifest and apply it
    login.run(f"cat > /tmp/{NIM_NAME}.yaml << 'MANIFEST'\n{nim_yaml}MANIFEST")
    result = login.run(f"kubectl apply -f /tmp/{NIM_NAME}.yaml")
    assert result.exit_code == 0, f"kubectl apply failed: {result.stderr}"
    mo.md(f"NIM deployment and service created: **{NIM_NAME}**")

    nim_deployed = True
    return (nim_deployed,)


# --------------------------------------------------------------------------- #
# Wait for NIM to become ready
# --------------------------------------------------------------------------- #
@app.cell
def wait_for_nim(login, NAMESPACE, NIM_NAME, time, nim_deployed):
    # @tested-docs: snippet wait-for-nim
    # @tested-docs: doc-page hello-world-for-nims-on-cks/2-deploy-nim
    mo.md(f"Waiting for **{NIM_NAME}** pod to become ready (up to 10 minutes)...")

    for attempt in range(40):  # 10 min max (40 x 15s)
        result = login.run(
            f"kubectl get pods -n {NAMESPACE} -l app={NIM_NAME} "
            "-o jsonpath='{.items[0].status.conditions[?(@.type==\"Ready\")].status}'"
        )
        if result.stdout.strip().strip("'") == "True":
            mo.md(f"NIM pod is **ready** (took ~{(attempt + 1) * 15}s)")
            break

        # Show current status for debugging
        if attempt % 4 == 0:
            status_result = login.run(
                f"kubectl get pods -n {NAMESPACE} -l app={NIM_NAME} "
                "--no-headers"
            )
            mo.md(f"_Attempt {attempt + 1}: {status_result.stdout.strip()}_")

        time.sleep(15)
    else:
        # Dump logs for debugging before failing
        login.run(
            f"kubectl logs -n {NAMESPACE} -l app={NIM_NAME} --tail=30"
        )
        raise TimeoutError(
            f"NIM pod did not become ready within 10 minutes"
        )

    nim_ready = True
    return (nim_ready,)


# --------------------------------------------------------------------------- #
# Query the NIM — chat completions
# --------------------------------------------------------------------------- #
@app.cell
def query_nim(login, NAMESPACE, NIM_NAME, NIM_MODEL, json, nim_ready):
    # @tested-docs: snippet query-nim
    # @tested-docs: doc-page hello-world-for-nims-on-cks/3-query-nim
    payload = json.dumps({
        "model": NIM_MODEL,
        "messages": [
            {"role": "user", "content": "What is CoreWeave in one sentence?"}
        ],
        "max_tokens": 128,
    })

    # Query via a temporary curl pod in the cluster
    result = login.run(
        f"kubectl run curl-test --rm -i --restart=Never "
        f"--image=curlimages/curl -- "
        f"curl -s http://{NIM_NAME}.{NAMESPACE}.svc.cluster.local:8000/v1/chat/completions "
        f"-H 'Content-Type: application/json' "
        f"-d '{payload}'"
    )
    assert result.exit_code == 0, f"NIM query failed: {result.stderr}"

    # Extract JSON from stdout — kubectl appends "pod deleted" text after the response
    raw = result.stdout.strip()
    # Find the JSON object boundaries
    start = raw.index('{')
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == '{': depth += 1
        elif ch == '}': depth -= 1
        if depth == 0:
            json_str = raw[start:i+1]
            break
    response = json.loads(json_str)
    assert "choices" in response, f"Unexpected response: {result.stdout[:200]}"

    answer = response["choices"][0]["message"]["content"]
    mo.md(
        f"**NIM response:**\n\n> {answer}\n\n"
        f"_Model: {response.get('model', 'unknown')}, "
        f"tokens: {response.get('usage', {}).get('total_tokens', '?')}_"
    )
    return (response,)


# --------------------------------------------------------------------------- #
# Verify via port-forward + external curl (alternative access pattern)
# --------------------------------------------------------------------------- #
@app.cell
def query_via_service(login, NAMESPACE, NIM_NAME, NIM_MODEL, json, response):
    # @tested-docs: snippet query-via-service
    # @tested-docs: doc-page hello-world-for-nims-on-cks/3-query-nim
    payload = json.dumps({
        "model": NIM_MODEL,
        "messages": [
            {"role": "user", "content": "Say hello in three words."}
        ],
        "max_tokens": 32,
    })

    # Second query via temporary pod to confirm service DNS works
    result = login.run(
        f"kubectl run curl-test-2 --rm -i --restart=Never "
        f"--image=curlimages/curl -- "
        f"curl -s http://{NIM_NAME}.{NAMESPACE}.svc.cluster.local:8000/v1/chat/completions "
        f"-H 'Content-Type: application/json' "
        f"-d '{payload}'"
    )
    assert result.exit_code == 0, f"Service query failed: {result.stderr}"

    # Extract JSON — kubectl appends pod lifecycle text
    raw = result.stdout.strip()
    start = raw.index('{')
    depth = 0
    for i, ch in enumerate(raw[start:], start):
        if ch == '{': depth += 1
        elif ch == '}': depth -= 1
        if depth == 0:
            json_str = raw[start:i+1]
            break
    svc_response = json.loads(json_str)
    assert "choices" in svc_response, f"Unexpected response: {result.stdout[:200]}"
    mo.md(f"**Service DNS query works:** {svc_response['choices'][0]['message']['content']}")

    queries_done = True
    return (queries_done,)


# --------------------------------------------------------------------------- #
# Cleanup
# --------------------------------------------------------------------------- #
@app.cell
def cleanup(login, NAMESPACE, NIM_NAME, queries_done):
    # @tested-docs: snippet cleanup
    # @tested-docs: doc-page hello-world-for-nims-on-cks/4-cleanup
    result = login.run(f"kubectl delete -f /tmp/{NIM_NAME}.yaml --ignore-not-found")
    login.run(
        f"kubectl delete secret ngc-credentials ngc-api-key "
        f"-n {NAMESPACE} --ignore-not-found"
    )
    login.run(f"rm -f /tmp/{NIM_NAME}.yaml")
    login.close()
    mo.md("All NIM resources cleaned up")


if __name__ == "__main__":
    app.run()
