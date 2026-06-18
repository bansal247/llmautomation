import json
import subprocess
import time
from pathlib import Path

import requests

# project root = llmautomation/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

COMFY_ROOT = PROJECT_ROOT / "ComfyUI_windows_portable"
WORKFLOW_FILE = PROJECT_ROOT / "comfy_code" / "piyagu_comfy_api_v1.json"

COMFY_URL = "http://127.0.0.1:8188"
COMFY_PROCESS = None

def start_comfyui():
    try:
        requests.get(COMFY_URL, timeout=2)
        print("ComfyUI already running")
        return
    except Exception:
        pass

    python_exe = COMFY_ROOT / "python_embeded" / "python.exe"
    main_py = COMFY_ROOT / "ComfyUI" / "main.py"

    if not python_exe.exists():
        raise FileNotFoundError(
            f"ComfyUI python not found:\n{python_exe}"
        )

    if not main_py.exists():
        raise FileNotFoundError(
            f"ComfyUI main.py not found:\n{main_py}"
        )

    print("Starting ComfyUI...")
    print("COMFY_ROOT:", COMFY_ROOT)

    COMFY_PROCESS = subprocess.Popen(
        [
            str(python_exe),
            "-s",
            str(main_py),
            "--windows-standalone-build",
            "--fast",
            "fp16_accumulation"
        ],
        cwd=str(COMFY_ROOT)
    )

    wait_for_comfyui()

def wait_for_comfyui(timeout=600):
    start = time.time()

    while time.time() - start < timeout:
        try:
            requests.get(COMFY_URL, timeout=5)
            print("ComfyUI is ready")
            return
        except Exception:
            time.sleep(2)

    raise RuntimeError("ComfyUI did not start")

def upload_image(image_path):
    with open(image_path, "rb") as f:
        r = requests.post(
            f"{COMFY_URL}/upload/image",
            files={"image": f}
        )

    r.raise_for_status()

    return r.json()["name"]

def load_workflow():
    with WORKFLOW_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)

def load_prompts():
    with (PROJECT_ROOT / "comfy_code" / "comfy_prompts.json").open("r", encoding="utf-8") as f:
        return json.load(f)

def free_resources():
    response = requests.post(
        "http://127.0.0.1:8188/free",
        json={
            "unload_models": True,
            "free_memory": True
        }
    )
    response.raise_for_status()
    return response

def run_workflow(
    image_path,
    prompt,
    workflow,
    output_prefix="output"
):

    uploaded_filename = upload_image(image_path)

    # Input image
    workflow["41"]["inputs"]["image"] = uploaded_filename

    # Prompt
    workflow["170:151"]["inputs"]["prompt"] = prompt

    # Output filename prefix
    workflow["9"]["inputs"]["filename_prefix"] = output_prefix

    r = requests.post(
        f"{COMFY_URL}/prompt",
        json={"prompt": workflow}
    )

    r.raise_for_status()

    prompt_id = r.json()["prompt_id"]

    print("Prompt ID:", prompt_id)

    while True:
        history = requests.get(
            f"{COMFY_URL}/history/{prompt_id}"
        ).json()

        if history:
            print("Generation completed")
            return prompt_id

        time.sleep(1)

def debug_paths():
    print("PROJECT_ROOT =", PROJECT_ROOT)
    print("COMFY_ROOT =", COMFY_ROOT)
    print("WORKFLOW_FILE =", WORKFLOW_FILE)

    print(
        "python.exe exists =",
        (COMFY_ROOT / "python_embeded" / "python.exe").exists()
    )

    print(
        "main.py exists =",
        (COMFY_ROOT / "ComfyUI" / "main.py").exists()
    )

    print(
        "workflow exists =",
        WORKFLOW_FILE.exists()
    )

def stop_comfyui():
    global COMFY_PROCESS

    if COMFY_PROCESS is not None:
        COMFY_PROCESS.terminate()
        COMFY_PROCESS.wait(timeout=30)
        COMFY_PROCESS = None

        print("ComfyUI stopped")