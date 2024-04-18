from huggingface_hub import snapshot_download
from os import symlink
from getpass import  getuser


hardcoded_version: str = '1c86eca4355ecc3e955a70198a7067da7858cec6'
hardcoded_model: str = 'Llama-2-70b-chat'
hardcoded_model_author: str = 'meta-llama'


snapshot_download(
    repo_id=hardcoded_model,
    revision=f"{hardcoded_model_author}/{hardcoded_model}"
)

symlink(
    src=f"/home/{getuser()}/.cache/huggingface/hub/models--{hardcoded_model_author}--{hardcoded_model}/snapshots/{hardcoded_version}",
    dst=f"/home/{getuser()}/.model__{hardcoded_model_author}__{hardcoded_model}"
)
