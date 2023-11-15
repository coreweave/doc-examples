FROM ghcr.io/coreweave/ml-containers/torch:29c37fa-nccl-cuda12.1.1-nccl2.18.3-1-torch2.0.1-vision0.15.2-audio2.0.2

RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y git build-essential \
    python3 python3-pip gcc wget

# setting build related env vars
ENV CUDA_DOCKER_ARCH=all
ENV LLAMA_CUBLAS=1

# Install depencencies
RUN python3 -m pip install --upgrade pip pytest cmake scikit-build setuptools fastapi uvicorn sse-starlette pydantic-settings starlette-context

# Install llama-cpp-python (build with cuda)
RUN CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python
RUN mkdir -p /opt/runtime
COPY main.py /opt/runtime
WORKDIR /opt/runtime
ENTRYPOINT ["python3","main.py"]