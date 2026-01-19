import requests
import json
import time
import os

CONFIG_FILE = "config.json"

def get_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"ollama_api_url": "http://localhost:11434/api"}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

OLLAMA_API_URL = get_config().get("ollama_api_url", "http://localhost:11434/api")

class OllamaClient:
    def __init__(self, base_url=None):
        if base_url:
            self.base_url = base_url
        else:
            self.base_url = get_config().get("ollama_api_url", "http://localhost:11434/api")

    def list_models(self):
        try:
            response = requests.get(f"{self.base_url}/tags")
            response.raise_for_status()
            models = response.json().get('models', [])
            return [m['name'] for m in models]
        except Exception as e:
            print(f"Error listing models: {e}")
            return []

    def generate(self, model, prompt, system=None, options=None, stream=False):
        """
        Generates text. Returns dict with 'response', 'total_duration', 'eval_count', 'eval_duration' etc.
        If stream=True, yields chunks of the response.
        """
        url = f"{self.base_url}/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if options:
            payload["options"] = options

        try:
            if stream:
                return self._generate_stream(url, payload)
            
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

    def _generate_stream(self, url, payload):
        try:
            with requests.post(url, json=payload, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        yield json.loads(line)
        except Exception as e:
            yield {"error": str(e)}

    def check_model_availability(self, model_name):
        models = self.list_models()
        return model_name in models

    def show_model_info(self, model_name):
        """
        Returns model details (quantization, context length, etc.)
        """
        url = f"{self.base_url}/show"
        payload = {"name": model_name}
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error showing model info: {e}")
            return {}

    def pull_model(self, model_name, progress_callback=None):
        """
        Pulls a model. Yields progress dicts if stream=True (handled internally).
        """
        url = f"{self.base_url}/pull"
        payload = {"name": model_name, "stream": True}
        
        try:
            with requests.post(url, json=payload, stream=True) as r:
                r.raise_for_status()
                for line in r.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if progress_callback:
                                progress_callback(data)
                        except:
                            pass
            return True
        except Exception as e:
            print(f"Pull error: {e}")
            if progress_callback:
                progress_callback({"error": str(e)})
            return False

    def delete_model(self, model_name):
        """
        Deletes a model from Ollama.
        """
        url = f"{self.base_url}/delete"
        payload = {"name": model_name}
        try:
            response = requests.delete(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Delete error: {e}")
            return False
