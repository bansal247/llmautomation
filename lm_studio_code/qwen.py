import requests
import time
from .lm_prompt import prompt
import base64

BASE_URL = "http://127.0.0.1:1234"
MODEL_NAME = "qwen3.5-35b-a3b"
CONTEXT_LENGTH = 25000

def get_loaded_model():
    try:
        r = requests.get(f"{BASE_URL}/api/v0/models", timeout=10)
        r.raise_for_status()
        data = r.json()

        # Adjust based on your LM Studio version
        if isinstance(data, list) and data:
            return data[0].get("id") or data[0].get("model")

        if isinstance(data, dict):
            loaded = data.get("data", [])
            if loaded:
                return loaded[0].get("id") or loaded[0].get("model")

        return None

    except Exception as e:
        print(f"Could not determine loaded model: {e}")
        return None


def load_model_if_needed(model_name=MODEL_NAME, context_length=CONTEXT_LENGTH):
    loaded_model = get_loaded_model()

    if loaded_model and model_name.lower() in loaded_model.lower():
        print(f"Model already loaded: {loaded_model}")
        return False

    print(f"Loading model: {model_name}")

    r = requests.post(
        f"{BASE_URL}/api/v1/models/load",
        json={
            "model": model_name,
            "context_length": context_length,
        },
        timeout=600,
    )

    r.raise_for_status()
    return r.json()


def generate_response(image_path):
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()

    response = requests.post(
        f"{BASE_URL}/api/v1/chat",
        headers={"Content-Type": "application/json"},
        json={
            "model": MODEL_NAME,
            "input": [
                {
                    "type": "text",
                    "content": prompt
                },
                {
                    "type": "image",
                    "data_url": f"data:image/jpeg;base64,{image_b64}"
                }
            ],
            "temperature": 0
        },
        timeout=600
    )

    response.raise_for_status()
    return response.json()

def unload_model(model_name=MODEL_NAME):
    r = requests.post(
        f"{BASE_URL}/api/v1/models/unload",
        json={
            "instance_id": model_name,
        },
        timeout=600
    )
    r.raise_for_status()
    return r.json()