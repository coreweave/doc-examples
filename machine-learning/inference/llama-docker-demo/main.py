from llama_cpp import Llama
from sys import argv
from os import environ

class InferMixins:
    def load_model(self,model_path: str = '/var/model/ggml-model-f16.gguf', gpu: bool = True):
        self.ngpu = 0
        if gpu == True:
            ngpu = -1
        self.model = Llama(model_path=model_path,
                           n_gpu_layers=ngpu)
    def run_prompt(self, prompt: str = 'Name the planets in the solar system?'):
        self.output = self.model(f"Q: {prompt} A: ",
                          max_tokens=0,
                          stop=["Q:"],
                          echo=True,
                          stream=True)
    def extract_outupt(self,output: str):
        return output['choices'][0]['text']
    def print_token(self, token: str):
        print(self.extract_outupt(token),end='')
    def stream_output(self):
        for token in self.output:
            self.print_token(token)
class InferMain(InferMixins):
    def __init__(self,
                 model_path: str = '/var/model/ggml-model-f16.gguf',
                 gpu: bool = True):
        self.load_model(model_path,gpu)


if __name__ == '__main__':
    x = InferMain()
    prompt_run = False
    if len(argv) > 1:
        x.run_prompt(argv[1])
        prompt_run = True
    if prompt_run is False:
        x.run_prompt(environ['PROMPT'])
        prompt_run = True
    if prompt_run is False:
        raise Exception('No prompt specified. Please specify a prompt using a command line argument or the PROMPT environment variable.')
    if prompt_run is True:
        x.stream_output()