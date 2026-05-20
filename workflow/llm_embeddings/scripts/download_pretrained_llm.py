import sys
from huggingface_hub import snapshot_download

def download_model_repo(model_name: str, save_dir: str) -> None:
    snapshot_download(
        repo_id=model_name,
        local_dir=save_dir,
        local_dir_use_symlinks=False,
    )

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 workflow/scripts/download_pretrained_llm.py <model_name> <save_dir>")
        sys.exit(1)

    model_name = sys.argv[1]
    save_dir = sys.argv[2]
    download_model_repo(model_name, save_dir)