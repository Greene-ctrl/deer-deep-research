from huggingface_hub import HfApi
import os
import time
from pathlib import Path

token = os.environ.get("HF_TOKEN")
if not token:
    print("HF_TOKEN environment variable not set.")
    exit(1)

api = HfApi(token=token)
repo_id = "AUXteam/DeerFlow"

def upload_all():
    print(f"Uploading files to {repo_id}...")

    # 1. Upload Folder
    try:
        api.upload_folder(
            folder_path=".",
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=[
                "backend/.venv/*",
                "frontend/node_modules/*",
                "frontend/.next/*",
                "logs/*",
                ".git/*",
                "__pycache__/*",
                "*.pyc",
                "scripts/hf_upload.py",
            ]
        )
        print("Folder upload complete!")
    except Exception as e:
        print(f"Folder upload failed: {e}")

    # 2. Force Upload Critical Files
    files_to_force = [
        "backend/src/gateway/routers/chat.py",
        "backend/src/gateway/routers/models.py",
        "backend/src/agents/middlewares/thread_data_middleware.py",
        "backend/src/models/factory.py",
        "backend/src/agents/lead_agent/agent.py",
        "config.example.yaml",
        "README.md",
        "Dockerfile",
        "scripts/start-hf.sh"
    ]

    for filepath in files_to_force:
        if os.path.exists(filepath):
            print(f"Force uploading {filepath}...")
            try:
                api.upload_file(
                    path_or_fileobj=filepath,
                    path_in_repo=filepath,
                    repo_id=repo_id,
                    repo_type="space"
                )
                print(f"Successfully force uploaded {filepath}")
            except Exception as e:
                print(f"Failed to upload {filepath}: {e}")

if __name__ == "__main__":
    upload_all()
