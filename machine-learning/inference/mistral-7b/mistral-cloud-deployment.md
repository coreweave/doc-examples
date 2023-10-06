> This is exactly the same as [readme.md](./readme.md), except with absolute links to the files and this notation.

 # Mistral 7B on CoreWeave Quickstart Guide

This quickstart deploys the Mistral 7B AI model as a Knative inference Service on CoreWeave Cloud using RTX A5000 GPUs. It initially uses one instance, scales up to ten on demand, and scales to zero when idle.

## Prerequisites

Follow the [Get Started with Kubernetes](https://docs.coreweave.com/coreweave-kubernetes/getting-started) guide to configure `kubectl` for CoreWeave Cloud, and set the preferred context. For example:

```bash
$ kubectl config use-context coreweave
```

## Create the Hugging Face Secret Token

Retrieve a [User Access Token from Hugging Face](https://huggingface.co/docs/hub/security-tokens), then Base64 encode the token.

```bash
$ echo <hugging-face-token> | base64
```

[Download `hugging-face-token.yaml`](https://github.com/coreweave/doc-examples/blob/main/machine-learning/inference/mistral-7b/hugging-face-token.yaml), replace `<base64-token>` with the encoded token, then deploy it as a Secret in the Namespace.

```bash
$ kubectl apply -f hugging-face-token.yaml
secret/hugging-face-token created
```
## Create the Inference Service

[Download `mistral-7b.yaml`](https://github.com/coreweave/doc-examples/blob/main/machine-learning/inference/mistral-7b/mistral-7b.yaml) and deploy it in the Namespace.

```bash
$ kubectl apply -f mistral-7b.yaml
```

Wait until the Service is ready, then retrieve the inference URL.

```bash
$ kubectl get ksvc mistral-7b
NAME         URL               LATESTCREATED      LATESTREADY        READY   REASON
mistral-7b   <inference-url>   mistral-7b-00001   mistral-7b-00001   True
```

To see detailed Revision status, assuming the Revision is `mistral-7b-00001`:

```bash
$ kubectl get revision mistral-7b-00001 -o yaml
```

## Test the Inference Service

Use any OpenAI API-compatible client to test the inference Service.

### With `curl`

Replace `<inference-url>` with the URL shown by `kubectl get ksvc mistral-7b`.

```bash
$ curl <inference-url>/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mistralai/Mistral-7B-v0.1",
    "prompt": "The Mistral is",
    "max_tokens": 200,
    "temperature": 0.7,
    "stop": "."
  }'

{"id":"cmpl-a78e72dc911f44e2981741ca71b2c9d6","object":"text_completion","created":1696551044,"model":"mistralai/Mistral-7B-v0.1","choices":[{"index":0,"text":" a modern 42-foot sailboat specially designed for the high seas, making it the most advanced in its class","logprobs":null,"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"total_tokens":31,"completion_tokens":26}}
```

### With Python

[Download the `test-inference.py` example](https://github.com/coreweave/doc-examples/blob/main/machine-learning/inference/mistral-7b/test-inference.py) and edit it to replace `<inference-url>` with the URL shown by `kubectl get ksvc mistral-7b`.

Then, install the `openai` Python package.

```bash
$ pip install openai
```

Run the Python script.

```bash
$ python test-inference.py
{'id': 'cmpl-7801cd1a9908451e82a12933385f2780', 'object': 'text_completion', 'created': 1696599387, 'model': 'mistralai/Mistral-7B-v0.1', 'choices': [{'index': 0, 'text': ' a cool wind that blows across the Mediterranean, for many centuries it has been a welcome guest in the South of France', 'logprobs': None, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 5, 'total_tokens': 30, 'completion_tokens': 25}}
```
