# `llama-docker-demo`
This repository contains a basic demonstration of text generation with LLMs such as Llama.
Please keep in mind that this is not a "reference implementation", and should never be used in production.
## Prerequisites
* Docker
* NVIDIA Container Toolkit
* At least 140GB VRAM (on one or more GPUs)
* NVIDIA Drivers and CUDA
* An LLM converted to `gguf` format, such as Llama 2 converted using the `convert.py` script in this repository: https://github.com/ggerganov/llama.cpp

## Quickstart
1. Clone this repository: `git clone https://github.com/coreweave/doc-examples`
2. Change directory to this project: `cd doc-examples/machine-learning/inference/llama-docker-demo`
3. Build Docker Image: `docker build -t llama-docker-demo .`
4. Run docker image: `docker run --gpus=all --cap-add SYS_RESOURCE -e USE_MLOCK=0 -e MODEL=/var/model/ggml-model-f16.gguf -v /home/$USER/llama/llama-2-70b-chat:/var/model -ti llama-docker-demo "what is a hello world?"`
   * Make sure to replace `/home/$USER/llama/llama-2-70b-chat` with the path to folder containing your `gguf` model if it’s located somewhere else.
   * You can replace `"what is a hello world?"` with whatever prompt you want.